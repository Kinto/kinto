from .support import (BaseWebTest, unittest, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class CollectionViewTest(BaseWebTest, unittest.TestCase):

    collections_url = '/buckets/beers/collections'
    collection_url = '/buckets/beers/collections/barley'

    def setUp(self):
        super(CollectionViewTest, self).setUp()
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

    def test_collections_do_not_support_post(self):
        self.app.post(self.collections_url, headers=self.headers,
                      status=405)

    def test_collections_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'barley')

    def test_collections_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/collections/__barley__',
                          MINIMALIST_COLLECTION,
                          headers=self.headers,
                          status=400)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collections_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_collections_are_isolated_by_bucket(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(other_bucket, headers=self.headers, status=404)

    def test_create_permissions_can_be_added_on_collections(self):
        collection = MINIMALIST_COLLECTION.copy()
        collection['permissions'] = {'record:create': ['fxa:user']}
        resp = self.app.put_json('/buckets/beers/collections/barley',
                                 collection,
                                 headers=self.headers,
                                 status=200)
        permissions = resp.json['permissions']
        self.assertIn('fxa:user', permissions['record:create'])

    def test_wrong_create_permissions_cannot_be_added_on_collections(self):
        collection = MINIMALIST_COLLECTION.copy()
        collection['permissions'] = {'collection:create': ['fxa:user']}
        self.app.put_json('/buckets/beers/collections/barley',
                          collection,
                          headers=self.headers,
                          status=400)

    def test_collections_can_handle_arbitrary_attributes(self):
        collection = MINIMALIST_COLLECTION.copy()
        fingerprint = "5866f245a00bb3a39100d31b2f14d453"
        collection['data'] = {'fingerprint': fingerprint}
        resp = self.app.put_json('/buckets/beers/collections/barley',
                                 collection,
                                 headers=self.headers,
                                 status=200)
        data = resp.json['data']
        self.assertIn('fingerprint', data)
        self.assertEqual(data['fingerprint'], fingerprint)


class CollectionDeletionTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley'

    def setUp(self):
        super(CollectionDeletionTest, self).setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        r = self.app.post_json(self.collection_url + '/records',
                               MINIMALIST_RECORD,
                               headers=self.headers)
        record_id = r.json['data']['id']
        self.record_url = self.collection_url + '/records/%s' % record_id
        self.app.delete(self.collection_url, headers=self.headers)

    def test_collections_can_be_deleted(self):
        self.app.get(self.collection_url, headers=self.headers,
                     status=404)

    def test_records_of_collection_are_deleted_too(self):
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.get(self.record_url, headers=self.headers, status=404)

        # Verify tombstones
        resp = self.app.get('%s/records?_since=0' % self.collection_url,
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)
