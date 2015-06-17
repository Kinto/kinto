from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)
from cliquet.tests.support import authorize


class BucketViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super(BucketViewTest, self).setUp()
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'read': ['system.Authenticated']}
        resp = self.app.put_json(self.record_url,
                                 bucket,
                                 headers=self.headers)
        self.record = resp.json['data']

    def get_app_settings(self, extra=None):
        settings = super(BucketViewTest, self).get_app_settings(extra)
        # Give the right to list buckets (for self.principal and alice).
        settings['cliquet.bucket_read_principals'] = 'system.Authenticated'
        return settings

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

    def test_create_permissions_can_be_added_on_buckets(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'collection:create': ['fxa:user'],
                                 'group:create': ['fxa:user']}
        resp = self.app.put_json('/buckets/beers',
                                 bucket,
                                 headers=self.headers,
                                 status=200)
        permissions = resp.json['permissions']
        self.assertIn('fxa:user', permissions['collection:create'])
        self.assertIn('fxa:user', permissions['group:create'])

    def test_wrong_create_permissions_cannot_be_added_on_buckets(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'record:create': ['fxa:user']}
        self.app.put_json('/buckets/beers',
                          bucket,
                          headers=self.headers,
                          status=400)


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

    def get_app_settings(self, extra=None):
        settings = super(BucketDeletionTest, self).get_app_settings(extra)
        # Give the permission to read, to get an explicit 404 once deleted.
        settings['cliquet.bucket_read_principals'] = self.principal
        return settings

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
