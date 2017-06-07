import unittest

from kinto.core.testing import get_user_headers

from .support import (BaseWebTest, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class CollectionViewTest(BaseWebTest, unittest.TestCase):

    collections_url = '/buckets/beers/collections'
    collection_url = '/buckets/beers/collections/barley'

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        resp = self.app.put_json(self.collection_url,
                                 MINIMALIST_COLLECTION,
                                 headers=self.headers)
        self.record = resp.json['data']

    def test_collection_endpoint_lists_them_all(self):
        resp = self.app.get(self.collections_url, headers=self.headers)
        records = resp.json['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'barley')

    def test_collections_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'barley')

    def test_collections_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/collections/__barley__',
                          MINIMALIST_COLLECTION,
                          headers=self.headers,
                          status=400)

    def test_collections_should_reject_unaccepted_request_content_type(self):
        headers = {**self.headers, 'Content-Type': 'text/plain'}
        self.app.put('/buckets/beers/collections/barley',
                     MINIMALIST_COLLECTION,
                     headers=headers,
                     status=415)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collections_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_unknown_collection_raises_404(self):
        other_collection = self.collection_url.replace('barley', 'pills')
        resp = self.app.get(other_collection, headers=self.headers, status=404)
        self.assertEqual(resp.json['details']['id'], 'pills')
        self.assertEqual(resp.json['details']['resource_name'], 'collection')

    def test_collections_are_isolated_by_bucket(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(other_bucket, headers=self.headers, status=404)

    def test_create_permissions_can_be_added_on_collections(self):
        collection = {**MINIMALIST_COLLECTION, 'permissions': {'record:create': ['fxa:user']}}
        resp = self.app.put_json('/buckets/beers/collections/barley',
                                 collection,
                                 headers=self.headers,
                                 status=200)
        permissions = resp.json['permissions']
        self.assertIn('fxa:user', permissions['record:create'])

    def test_wrong_create_permissions_cannot_be_added_on_collections(self):
        collection = {**MINIMALIST_COLLECTION, 'permissions': {'collection:create': ['fxa:user']}}
        self.app.put_json('/buckets/beers/collections/barley',
                          collection,
                          headers=self.headers,
                          status=400)

    def test_collections_can_handle_arbitrary_attributes(self):
        fingerprint = "5866f245a00bb3a39100d31b2f14d453"
        collection = {**MINIMALIST_COLLECTION, 'data': {'fingerprint': fingerprint}}
        resp = self.app.put_json('/buckets/beers/collections/barley',
                                 collection,
                                 headers=self.headers,
                                 status=200)
        data = resp.json['data']
        self.assertIn('fingerprint', data)
        self.assertEqual(data['fingerprint'], fingerprint)

    def test_collections_can_be_filtered_by_arbitrary_attribute(self):
        collection = {**MINIMALIST_COLLECTION, 'data': {'size': 3}}
        self.app.put_json('/buckets/beers/collections/moderator',
                          collection,
                          headers=self.headers)
        resp = self.app.get('/buckets/beers/collections?has_size=true&min_size=2',
                            headers=self.headers)
        data = resp.json['data']
        self.assertEqual(len(data), 1)


class CollectionDeletionTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley'

    def setUp(self):
        super().setUp()
        bucket = {**MINIMALIST_BUCKET,
                  'permissions': {'collection:create': ['system.Everyone'],
                                  'read': ['system.Everyone']}}
        self.app.put_json('/buckets/beers', bucket,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        resp = self.app.post_json(self.collection_url + '/records',
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.previous_ts = resp.headers['ETag']
        record_id = resp.json['data']['id']
        self.record_url = self.collection_url + '/records/{}'.format(record_id)
        self.app.delete(self.collection_url, headers=self.headers)

    def test_collections_can_be_deleted(self):
        self.app.get(self.collection_url, headers=self.headers, status=404)

    def test_collections_can_be_deleted_in_bulk(self):
        alice_headers = get_user_headers('alice')
        self.app.put_json('/buckets/beers/collections/1',
                          MINIMALIST_COLLECTION, headers=self.headers)
        self.app.put_json('/buckets/beers/collections/2',
                          MINIMALIST_COLLECTION, headers=alice_headers)
        self.app.put_json('/buckets/beers/collections/3',
                          MINIMALIST_COLLECTION, headers=alice_headers)
        self.app.delete('/buckets/beers/collections',
                        headers=alice_headers)
        resp = self.app.get('/buckets/beers/collections', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)

    def test_records_of_collection_are_deleted_too(self):
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.get(self.record_url, headers=self.headers, status=404)

        # Verify tombstones
        resp = self.app.get('{}/records?_since=0'.format(self.collection_url),
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_timestamps_are_refreshed_when_collection_is_recreated(self):
        # Kinto/kinto#1223
        # Recreate with same name.
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        resp = self.app.get(self.collection_url + '/records', headers=self.headers)
        records_ts = resp.headers['ETag']
        self.assertNotEqual(self.previous_ts, records_ts)

    def test_can_be_created_after_deletion_with_if_none_match_star(self):
        headers = {**self.headers, 'If-None-Match': '*'}
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=headers, status=201)


class CollectionCreationTest(BaseWebTest, unittest.TestCase):

    collections_url = '/buckets/beers/collections'

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)

    def test_collection_can_be_created_with_post(self):
        r = self.app.post_json(self.collections_url,
                               MINIMALIST_COLLECTION,
                               headers=self.headers)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(len(r.json['data']['id']) == 8)

    def test_collection_can_be_specified_in_post(self):
        collection = 'barley'
        r = self.app.post_json(self.collections_url,
                               {'data': {'id': collection}},
                               headers=self.headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json['data']['id'], collection)

    def test_collection_already_exists_post(self):
        collection = "barley"
        self.app.post_json(self.collections_url,
                           {'data': {'id': collection}},
                           headers=self.headers)
        r = self.app.post_json(self.collections_url,
                               {'data': {'id': collection}},
                               headers=self.headers)
        self.assertEqual(r.json['data']['id'], collection)
        self.assertEqual(r.status_code, 200)
