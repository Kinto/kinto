import json
import mock
import re
import unittest

from kinto.core.testing import get_user_headers

from .support import (BaseWebTest, MINIMALIST_RECORD,
                      MINIMALIST_GROUP, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION)


class RecordsViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'
    _record_url = '/buckets/beers/collections/barley/records/{}'

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self._record_url.format(self.record['id'])

    def test_records_can_be_accessed_by_id(self):
        self.app.get(self.record_url, headers=self.headers)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_unknown_collection_raises_404(self):
        other_collection = self.collection_url.replace('barley', 'pills')
        resp = self.app.get(other_collection, headers=self.headers, status=404)
        self.assertEqual(resp.json['details']['id'], 'pills')
        self.assertEqual(resp.json['details']['resource_name'], 'collection')

    def test_unknown_record_raises_404(self):
        other_record = self.record_url.replace(self.record['id'], self.record['id']+'blah')
        response = self.app.get(other_record, headers=self.headers, status=404)
        self.assertEqual(response.json['details']['id'], self.record['id']+'blah')
        self.assertEqual(response.json['details']['resource_name'], 'record')

    def test_unknown_collection_does_not_query_timestamp(self):
        other_collection = self.collection_url.replace('barley', 'pills')
        patch = mock.patch.object(self.app.app.registry.storage,
                                  'collection_timestamp')
        self.addCleanup(patch.stop)
        mocked = patch.start()
        self.app.get(other_collection, headers=self.headers, status=404)
        self.assertFalse(mocked.called)

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
            record = {**MINIMALIST_RECORD, 'data': {
                **MINIMALIST_RECORD['data'],
                'name': 'Stout {}'.format(i)}
            }
            self.app.post_json(self.collection_url,
                               record,
                               headers=self.headers)

        response = self.app.get(self.collection_url + '?_sort=-name',
                                headers=self.headers)
        names = [i['name'] for i in response.json['data']]
        self.assertEqual(names,
                         ['Stout 2', 'Stout 1', 'Stout 0', 'Hulled Barley'])

    def test_wrong_create_permissions_cannot_be_added_on_records(self):
        record = {**MINIMALIST_RECORD, 'permissions': {'record:create': ['fxa:user']}}
        self.app.put_json(self.record_url,
                          record,
                          headers=self.headers,
                          status=400)

    def test_create_a_record_update_collection_timestamp(self):
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        old_timestamp = int(json.loads(collection_resp.headers['ETag']))
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.headers,
                           status=201)
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        new_timestamp = int(json.loads(collection_resp.headers['ETag']))
        assert old_timestamp < new_timestamp

    def test_create_a_record_without_id_generates_a_uuid(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers,
                                  status=201)
        regexp = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
                            r'[0-9a-f]{4}-[0-9a-f]{12}$')
        self.assertTrue(regexp.match(resp.json['data']['id']))

    def test_create_a_record_with_an_id_uses_it(self):
        record = {'data': dict(id='a-simple-id', **MINIMALIST_RECORD['data'])}
        resp = self.app.post_json(self.collection_url,
                                  record,
                                  headers=self.headers,
                                  status=201)
        self.assertEqual(resp.json['data']['id'], 'a-simple-id')

    def test_create_a_record_with_an_existing_id_returns_existing(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers,
                                  status=201)
        existing_id = resp.json['data']['id']
        record = {'data': {'id': existing_id, 'stars': 8}}
        resp = self.app.post_json(self.collection_url,
                                  record,
                                  headers=self.headers,
                                  status=200)
        self.assertNotIn('stars', resp.json['data'])

    def test_create_a_record_with_existing_from_someone_else_gives_403(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers,
                                  status=201)
        existing_id = resp.json['data']['id']
        record = {'data': {'id': existing_id, 'stars': 8}}
        resp = self.app.post_json(self.collection_url,
                                  record,
                                  headers=get_user_headers('tartanpion'),
                                  status=403)

    def test_update_a_record_update_collection_timestamp(self):
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        old_timestamp = int(json.loads(collection_resp.headers['ETag']))
        self.app.put_json(self.record_url,
                          MINIMALIST_RECORD,
                          headers=self.headers,
                          status=200)
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        new_timestamp = int(json.loads(collection_resp.headers['ETag']))
        assert old_timestamp < new_timestamp

    def test_delete_a_record_update_collection_timestamp(self):
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        old_timestamp = int(json.loads(collection_resp.headers['ETag']))
        self.app.delete(self.record_url,
                        headers=self.headers,
                        status=200)
        collection_resp = self.app.get(self.collection_url,
                                       headers=self.headers)
        new_timestamp = int(json.loads(collection_resp.headers['ETag']))
        assert old_timestamp < new_timestamp

    def test_record_is_accessible_by_group_member(self):
        # access as aaron
        self.aaron_headers = {**self.headers, **get_user_headers('aaron')}

        resp = self.app.get('/',
                            headers=self.aaron_headers,
                            status=200)

        self.create_group('beers', 'brewers', [resp.json['user']['id']])
        record = {**MINIMALIST_RECORD, 'permissions': {'read': ['/buckets/beers/groups/brewers']}}
        self.app.put_json(self.record_url,
                          record,
                          headers=self.headers,
                          status=200)

        self.app.get(self.record_url,
                     headers=self.aaron_headers,
                     status=200)

    def test_records_should_reject_unaccepted_request_content_type(self):
        headers = {**self.headers, 'Content-Type': 'text/plain'}
        self.app.put(self.record_url,
                     MINIMALIST_RECORD,
                     headers=headers,
                     status=415)

    def test_records_should_reject_unaccepted_client_accept(self):
        headers = {**self.headers, 'Accept': 'text/plain'}
        self.app.get(self.record_url,
                     MINIMALIST_RECORD,
                     headers=headers,
                     status=406)

    def test_records_should_accept_client_accept(self):
        headers = {**self.headers, 'Accept': '*/*'}
        self.app.get(self.record_url,
                     MINIMALIST_RECORD,
                     headers=headers,
                     status=200)

    def test_records_can_be_created_after_deletion(self):
        self.app.delete(self.record_url,
                        headers=self.headers,
                        status=200)
        headers = {**self.headers, 'If-None-Match': '*'}
        self.app.put_json(self.record_url, MINIMALIST_RECORD,
                          headers=headers, status=201)


class RecordsViewMergeTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'
    _record_url = '/buckets/beers/collections/barley/records/{}'

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        record = {**MINIMALIST_RECORD, 'data': {'grain': {'one': 1}}}
        resp = self.app.post_json(self.collection_url, record,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self._record_url.format(self.record['id'])

    def test_merge_patch(self):
        headers = {**self.headers, 'Content-Type': 'application/merge-patch+json'}
        json = {'data': {'grain': {'two': 2}}}
        resp = self.app.patch_json(self.record_url,
                                   json,
                                   headers=headers,
                                   status=200)
        self.assertEquals(resp.json['data']['grain']['one'], 1)
        self.assertEquals(resp.json['data']['grain']['two'], 2)

    def test_merge_patch_remove_nones(self):
        headers = {**self.headers, 'Content-Type': 'application/merge-patch+json'}
        json = {'data': {'grain': {'one': None}}}
        resp = self.app.patch_json(self.record_url,
                                   json,
                                   headers=headers,
                                   status=200)
        self.assertNotIn('one', resp.json['data']['grain'])


class RecordsViewPatchTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'
    _record_url = '/buckets/beers/collections/barley/records/{}'

    def setUp(self):
        super().setUp()
        self.patch_headers = {**self.headers, 'Content-Type': 'application/json-patch+json'}

        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        record = {**MINIMALIST_RECORD, 'permissions': {
            'read': ['alice', 'carla'],
            'write': ['bob']
        }}
        resp = self.app.post_json(self.collection_url,
                                  record,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self._record_url.format(self.record['id'])

    def test_patch_add_permissions(self):
        json = [{'op': 'add', 'path': '/permissions/read/me', 'value': 'me'}]
        resp = self.app.patch_json(self.record_url,
                                   json,
                                   headers=self.patch_headers,
                                   status=200)

        perms = resp.json['permissions']
        self.assertIn('me', perms['read'])
        self.assertIn('alice', perms['read'])

    def test_patch_update_permissions(self):
        json = [{'op': 'add', 'path': '/permissions/read', 'value': ['me']}]
        resp = self.app.patch_json(self.record_url,
                                   json,
                                   headers=self.patch_headers,
                                   status=200)

        perms = resp.json['permissions']
        self.assertIn('me', perms['read'])
        self.assertNotIn(('alice', 'bob'), perms['read'])

    def test_patch_remove_permissions(self):
        json = [{'op': 'remove', 'path': '/permissions/read/alice'}]
        resp = self.app.patch_json(self.record_url,
                                   json,
                                   headers=self.patch_headers,
                                   status=200)
        perms = resp.json['permissions']
        self.assertNotIn('alice', perms['read'])

    def test_patch_move_permissions(self):
        json = [
            {'op': 'move', 'from': '/permissions/read/alice',
                           'path': '/data/old'}
        ]
        resp = self.app.patch_json(self.record_url,
                                   json,
                                   headers=self.patch_headers,
                                   status=200)

        perms = resp.json['permissions']
        data = resp.json['data']
        self.assertNotIn('alice', perms['read'])
        self.assertEquals('alice', data['old'])

    def test_patch_raises_400_on_wrong_path(self):
        json = [{'op': 'add', 'path': '/permissions/destroy/me'}]
        self.app.patch_json(self.record_url,
                            json,
                            headers=self.patch_headers,
                            status=400)


class RecordsViewFilterTest(BaseWebTest, unittest.TestCase):
    collection_url = '/buckets/beers/collections/barley/records'

    RECORDS = [
        {
            "id": "strawberry",
            "flavor": "strawberry",
            "attributes": {"ibu": 25, "seen_on": "2017-06-01"},
            "author": None,
        },
        {"id": "raspberry-1", "flavor": "raspberry", "attributes": {}},
        {"id": "raspberry-2", "flavor": "raspberry", "attributes": []},
        {
            "id": "raspberry-3",
            "flavor": "raspberry",
            "attributes": {"ibu": 25, "seen_on": "2017-06-01", "price": 9.99},
        },
    ]

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)

        for record in self.RECORDS:
            self.app.post_json(self.collection_url,
                               {"data": record},
                               headers=self.headers)

    def test_records_can_be_filtered_using_json(self):
        response = self.app.get(self.collection_url + '?flavor="strawberry"',
                                headers=self.headers)
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == 'strawberry'

    def test_records_can_be_filtered_with_object(self):
        query = self.collection_url + '?attributes={"ibu": 25, "seen_on": "2017-06-01"}'
        response = self.app.get(query,
                                headers=self.headers)
        assert len(response.json['data']) == 1
        assert response.json['data'][0]['id'] == 'strawberry'
