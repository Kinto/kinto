from .support import BaseWebTest, unittest


MINIMALIST_ITEM = dict()


class BucketViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super(BucketViewTest, self).setUp()
        resp = self.app.put_json(self.record_url,
                                 MINIMALIST_ITEM,
                                 headers=self.headers)
        self.record = resp.json  # XXX: ['data']

    def test_buckets_do_not_support_post(self):
        self.app.post(self.collection_url, headers=self.headers,
                      status=405)

    def test_buckets_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'beers')

    def test_collection_endpoint_lists_them_all(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['items']  # XXX: ['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'beers')

    def test_buckets_name_should_be_simple(self):
        self.app.put_json('/buckets/__beers__',
                          MINIMALIST_ITEM,
                          headers=self.headers,
                          status=400)

    def test_current_user_receives_write_permission_on_creation(self):
        pass


class BucketDeletionTest(BaseWebTest, unittest.TestCase):

    record_url = '/buckets/beers'

    def test_buckets_can_be_deleted(self):
        self.app.put_json(self.record_url, MINIMALIST_ITEM,
                          headers=self.headers)
        self.app.delete(self.record_url, headers=self.headers)
        self.app.get(self.record_url, headers=self.headers,
                     status=404)

    def test_every_collections_are_deleted_too(self):
        pass

    def test_every_groups_are_deleted_too(self):
        pass

    def test_every_records_are_deleted_too(self):
        pass

    def test_permissions_associated_are_deleted_too(self):
        pass
