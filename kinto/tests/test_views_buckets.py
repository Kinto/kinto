from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)
from cliquet.tests.support import authorize


class BucketViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super(BucketViewTest, self).setUp()
        resp = self.app.put_json(self.record_url,
                                 MINIMALIST_BUCKET,
                                 headers=self.headers)
        self.record = resp.json['data']

    @authorize(True, 'kinto.tests.support.AllowAuthorizationPolicy')
    def test_buckets_are_global_to_every_users(self):
        self.app.get(self.record_url, headers=get_user_headers('alice'))

    def test_buckets_do_not_support_post(self):
        self.app.post(self.collection_url, headers=self.headers,
                      status=405)

    def test_buckets_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'beers')

    def test_collection_endpoint_lists_them_all(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'beers')

    def test_buckets_name_should_be_simple(self):
        self.app.put_json('/buckets/__beers__',
                          MINIMALIST_BUCKET,
                          headers=self.headers,
                          status=400)

    def test_current_user_receives_write_permission_on_creation(self):
        pass


class BucketDeletionTest(BaseWebTest, unittest.TestCase):

    bucket_url = '/buckets/beers'
    collection_url = '/buckets/beers/collections/barley'
    group_url = '/buckets/beers/groups/moderators'

    def setUp(self):
        # Create a bucket with some objects.
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json(self.group_url, MINIMALIST_GROUP,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        r = self.app.post_json(self.collection_url + '/records',
                               MINIMALIST_RECORD,
                               headers=self.headers)
        record_id = r.json['data']['id']
        self.record_url = self.collection_url + '/records/%s' % record_id
        # Delete the bucket.
        self.app.delete(self.bucket_url, headers=self.headers)

    def test_buckets_can_be_deleted(self):
        self.app.get(self.bucket_url, headers=self.headers,
                     status=404)

    def test_every_collections_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(self.collection_url, headers=self.headers, status=404)

    def test_every_groups_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(self.group_url, headers=self.headers, status=404)

    def test_every_records_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.get(self.record_url, headers=self.headers, status=404)

    def test_permissions_associated_are_deleted_too(self):
        pass
