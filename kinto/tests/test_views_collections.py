from .support import BaseWebTest, unittest


MINIMALIST_ITEM = dict()


class CollectionViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections'
    record_url = '/buckets/beers/collections/barley'

    def test_collections_do_not_support_post(self):
        self.app.post(self.collection_url, headers=self.headers,
                      status=405)

    def test_collections_can_be_put_with_simple_name(self):
        response = self.app.put_json(self.record_url,
                                     MINIMALIST_ITEM,
                                     headers=self.headers)
        self.assertEqual(response.json['id'], 'barley')

    def test_collections_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/collections/__barley__',
                          MINIMALIST_ITEM,
                          headers=self.headers,
                          status=400)

    def test_collections_creation_fails_if_bucket_is_not_found(self):
        pass


class CollectionDeletionTest(BaseWebTest, unittest.TestCase):

    record_url = '/buckets/beers/collections/barley'

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
