from .support import BaseWebTest, unittest


MINIMALIST_ITEM = dict()


class CollectionViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections'
    record_url = '/buckets/beers/collections/barley'

    def setUp(self):
        super(CollectionViewTest, self).setUp()
        self.app.put_json('/buckets/beers', {}, headers=self.headers)
        resp = self.app.put_json(self.record_url,
                                 MINIMALIST_ITEM,
                                 headers=self.headers)
        self.record = resp.json  # XXX: ['data']

    def test_collection_endpoint_lists_them_all(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['items']  # XXX: ['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'barley')

    def test_collections_do_not_support_post(self):
        self.app.post(self.collection_url, headers=self.headers,
                      status=405)

    def test_collections_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'barley')

    def test_collections_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/collections/__barley__',
                          MINIMALIST_ITEM,
                          headers=self.headers,
                          status=400)

    def test_unknown_bucket_raises_404(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=404)

    def test_collections_are_isolated_by_bucket(self):
        other_bucket = self.record_url.replace('beers', 'water')
        self.app.get(other_bucket, headers=self.headers, status=404)

    def test_collections_creation_fails_if_bucket_is_not_found(self):
        pass


class CollectionDeletionTest(BaseWebTest, unittest.TestCase):

    record_url = '/buckets/beers/collections/barley'

    def setUp(self):
        super(CollectionDeletionTest, self).setUp()
        self.app.put_json('/buckets/beers', {}, headers=self.headers)

    def test_collections_can_be_deleted(self):
        self.app.put_json(self.record_url, MINIMALIST_ITEM,
                          headers=self.headers)
        self.app.delete(self.record_url, headers=self.headers)
        self.app.get(self.record_url, headers=self.headers,
                     status=404)

    def test_records_of_collection_are_deleted_too(self):
        pass

    def test_permissions_associated_are_deleted_too(self):
        pass
