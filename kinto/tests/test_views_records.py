import json
import mock

from kinto.core.utils import decode_header
from .support import (BaseWebTest, unittest, MINIMALIST_RECORD,
                      MINIMALIST_GROUP, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION, get_user_headers)


class RecordsViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'
    _record_url = '/buckets/beers/collections/barley/records/%s'

    def setUp(self):
        super(RecordsViewTest, self).setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self._record_url % self.record['id']

    def test_records_can_be_accessed_by_id(self):
        self.app.get(self.record_url, headers=self.headers)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_unknown_collection_raises_404(self):
        other_collection = self.collection_url.replace('barley', 'pills')
        self.app.get(other_collection, headers=self.headers, status=404)

    def test_parent_collection_is_fetched_only_once_in_batch(self):
        batch = {'requests': []}
        nb_create = 25
        for i in range(nb_create):
            request = {'method': 'POST',
                       'path': self.collection_url,
                       'body': MINIMALIST_RECORD}
            batch['requests'].append(request)

        with mock.patch.object(self.storage, 'get',
                               wraps=self.storage.get) as patched:
            self.app.post_json('/batch', batch, headers=self.headers)
            self.assertEqual(patched.call_count, 1)

    def test_individual_collections_can_be_deleted(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)
        self.app.delete(self.collection_url, headers=self.headers)
        resp = self.app.get(self.collection_url, headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_records_can_be_added_to_collections(self):
        response = self.app.get(self.record_url, headers=self.headers)
        record = response.json['data']
        del record['id']
        del record['last_modified']
        self.assertEquals(record, MINIMALIST_RECORD['data'])

    def test_records_are_isolated_by_bucket_and_by_collection(self):
        # By collection.
        self.app.put_json('/buckets/beers/collections/pills',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        other_collection = self.record_url.replace('barley', 'pills')
        self.app.get(other_collection, headers=self.headers, status=404)

        # By bucket.
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/sodas/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        other_bucket = self.record_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=404)

        # By bucket and by collection.
        self.app.put_json('/buckets/be',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/be/collections/ba',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        other = self.record_url.replace('barley', 'ba').replace('beers', 'be')
        self.app.get(other, headers=self.headers, status=404)

    def test_a_collection_named_group_do_not_interfere_with_groups(self):
        # Create a group.
        self.app.put_json('/buckets/beers/groups/test',
                          MINIMALIST_GROUP,
                          headers=self.headers)
        # Create a record in a collection named "group".
        self.app.put_json('/buckets/beers/collections/groups',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        collection_group = self.collection_url.replace('barley', 'groups')
        self.app.post_json(collection_group,
                           MINIMALIST_RECORD,
                           headers=self.headers)
        # There is still only one group.
        resp = self.app.get('/buckets/beers/groups', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)

    def test_records_can_be_filtered_on_any_field(self):
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.headers)
        response = self.app.get(self.collection_url + '?unknown=1',
                                headers=self.headers)
        self.assertEqual(len(response.json['data']), 0)

    def test_records_can_be_sorted_on_any_field(self):
        for i in range(3):
            record = MINIMALIST_RECORD.copy()
            record['data']['name'] = 'Stout %s' % i
            self.app.post_json(self.collection_url,
                               record,
                               headers=self.headers)

        response = self.app.get(self.collection_url + '?_sort=-name',
                                headers=self.headers)
        names = [i['name'] for i in response.json['data']]
        self.assertEqual(names,
                         ['Stout 2', 'Stout 1', 'Stout 0', 'Hulled Barley'])

    def test_wrong_create_permissions_cannot_be_added_on_records(self):
        record = MINIMALIST_RECORD.copy()
        record['permissions'] = {'record:create': ['fxa:user']}
        self.app.put_json(self.record_url,
                          record,
                          headers=self.headers,
                          status=400)

    def test_create_a_record_update_collection_timestamp(self):
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        old_timestamp = int(
            decode_header(json.loads(collection_resp.headers['ETag'])))
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.headers,
                           status=201)
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        new_timestamp = int(
            decode_header(json.loads(collection_resp.headers['ETag'])))
        assert old_timestamp < new_timestamp

    def test_update_a_record_update_collection_timestamp(self):
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        old_timestamp = int(
            decode_header(json.loads(collection_resp.headers['ETag'])))
        self.app.put_json(self.record_url,
                          MINIMALIST_RECORD,
                          headers=self.headers,
                          status=200)
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        new_timestamp = int(
            decode_header(json.loads(collection_resp.headers['ETag'])))
        assert old_timestamp < new_timestamp

    def test_delete_a_record_update_collection_timestamp(self):
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        old_timestamp = int(
            decode_header(json.loads(collection_resp.headers['ETag'])))
        self.app.delete(self.record_url,
                        headers=self.headers,
                        status=200)
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        new_timestamp = int(
            decode_header(json.loads(collection_resp.headers['ETag'])))
        assert old_timestamp < new_timestamp

    def test_record_is_accessible_by_group_member(self):
        # access as aaron
        self.aaron_headers = self.headers.copy()
        self.aaron_headers.update(**get_user_headers('aaron'))

        resp = self.app.get('/',
                            headers=self.aaron_headers,
                            status=200)

        self.create_group('beers', 'brewers', [resp.json['user']['id']])
        record = MINIMALIST_RECORD.copy()
        record['permissions'] = {'read': ['/buckets/beers/groups/brewers']}
        self.app.put_json(self.record_url,
                          record,
                          headers=self.headers,
                          status=200)

        self.app.get(self.record_url,
                     headers=self.aaron_headers,
                     status=200)

    def test_records_should_reject_unaccepted_request_content_type(self):
        headers = self.headers.copy()
        headers['Content-Type'] = 'text/plain'
        self.app.put(self.record_url,
                     MINIMALIST_RECORD,
                     headers=headers,
                     status=415)

    def test_records_should_reject_unaccepted_client_accept(self):
        headers = self.headers.copy()
        headers['Accept'] = 'text/plain'
        self.app.get(self.record_url,
                     MINIMALIST_RECORD,
                     headers=headers,
                     status=406)

    def test_records_should_accept_client_accept(self):
        headers = self.headers.copy()
        headers['Accept'] = '*/*'
        self.app.get(self.record_url,
                     MINIMALIST_RECORD,
                     headers=headers,
                     status=200)

    def test_records_can_be_created_after_deletion(self):
        self.app.delete(self.record_url,
                        headers=self.headers,
                        status=200)
        headers = self.headers.copy()
        headers['If-None-Match'] = '*'
        self.app.put_json(self.record_url, MINIMALIST_RECORD,
                          headers=headers, status=201)
