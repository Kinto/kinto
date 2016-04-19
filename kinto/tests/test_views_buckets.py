from pyramid.security import Authenticated

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class BucketViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super(BucketViewTest, self).setUp()
        resp = self.app.put_json(self.record_url,
                                 MINIMALIST_BUCKET,
                                 headers=self.headers)
        self.record = resp.json['data']

    def test_buckets_are_global_to_every_users(self):
        self.app.patch_json(self.record_url,
                            {'permissions': {'read': [Authenticated]}},
                            headers=self.headers)
        self.app.get(self.record_url, headers=get_user_headers('alice'))

    def test_buckets_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'beers')

    def test_buckets_names_can_have_underscores(self):
        bucket = MINIMALIST_BUCKET.copy()
        record_url = '/buckets/alexis_beers'
        resp = self.app.put_json(record_url,
                                 bucket,
                                 headers=self.headers)
        self.assertEqual(resp.json['data']['id'], 'alexis_beers')

    def test_nobody_can_list_buckets_by_default(self):
        self.app.get(self.collection_url,
                     headers=get_user_headers('alice'),
                     status=403)

    def test_nobody_can_read_bucket_information_by_default(self):
        self.app.get(self.record_url,
                     headers=get_user_headers('alice'),
                     status=403)

    def test_buckets_name_should_be_simple(self):
        self.app.put_json('/buckets/__beers__',
                          MINIMALIST_BUCKET,
                          headers=self.headers,
                          status=400)

    def test_buckets_should_reject_unaccepted_request_content_type(self):
        headers = self.headers.copy()
        headers['Content-Type'] = 'text/plain'
        self.app.put('/buckets/beers',
                     MINIMALIST_BUCKET,
                     headers=headers,
                     status=415)

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

    def test_buckets_can_handle_arbitrary_attributes(self):
        bucket = MINIMALIST_BUCKET.copy()
        public_key = "5866f245a00bb3a39100d31b2f14d453"
        bucket['data'] = {'public_key': public_key}
        resp = self.app.put_json('/buckets/beers',
                                 bucket,
                                 headers=self.headers,
                                 status=200)
        data = resp.json['data']
        self.assertIn('public_key', data)
        self.assertEqual(data['public_key'], public_key)


class BucketCreationTest(BaseWebTest, unittest.TestCase):
    def test_buckets_can_be_created_with_post(self):
        r = self.app.post_json('/buckets',
                               MINIMALIST_BUCKET,
                               headers=self.headers)
        self.assertEqual(r.status_code, 201)

    def test_bucket_id_can_be_specified_in_post(self):
        bucket = 'blog'
        r = self.app.post_json('/buckets',
                               {'data': {'id': bucket}},
                               headers=self.headers)
        self.assertEqual(r.json['data']['id'], bucket)

    def test_bucket_can_be_created_without_body_nor_contenttype(self):
        headers = self.headers.copy()
        headers.pop("Content-Type")
        self.app.put('/buckets/catalog', headers=headers)


class BucketReadPermissionTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super(BucketReadPermissionTest, self).setUp()
        bucket = MINIMALIST_BUCKET.copy()
        self.app.put_json(self.record_url,
                          bucket,
                          headers=self.headers)

    def get_app_settings(self, extra=None):
        settings = super(BucketReadPermissionTest,
                         self).get_app_settings(extra)
        # Give the right to list buckets (for self.principal and alice).
        settings['kinto.bucket_read_principals'] = Authenticated
        return settings

    def test_bucket_collection_endpoint_lists_them_all_for_everyone(self):
        resp = self.app.get(self.collection_url,
                            headers=get_user_headers('alice'))
        records = resp.json['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'beers')

    def test_everyone_can_read_bucket_information(self):
        resp = self.app.get(self.record_url, headers=get_user_headers('alice'))
        record = resp.json['data']
        self.assertEqual(record['id'], 'beers')


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
        settings['kinto.bucket_read_principals'] = self.principal
        return settings

    def test_buckets_can_be_deleted_in_bulk(self):
        self.app.put_json('/buckets/1', MINIMALIST_BUCKET,
                          headers=get_user_headers('alice'))
        self.app.put_json('/buckets/2', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/3', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.delete('/buckets', headers=self.headers)
        self.app.get('/buckets/1', headers=self.headers, status=200)
        self.app.get('/buckets/2', headers=self.headers, status=404)
        self.app.get('/buckets/3', headers=self.headers, status=404)

    def test_buckets_can_be_deleted(self):
        self.app.get(self.bucket_url, headers=self.headers,
                     status=404)

    def test_every_collections_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(self.collection_url, headers=self.headers, status=404)
        # Verify tombstones
        resp = self.app.get('%s/collections?_since=0' % self.bucket_url,
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_every_groups_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(self.group_url, headers=self.headers, status=404)
        # Verify tombstones
        resp = self.app.get('%s/groups?_since=0' % self.bucket_url,
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_every_records_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.get(self.record_url, headers=self.headers, status=404)

        # Verify tombstones
        resp = self.app.get('%s/records?_since=0' % self.collection_url,
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_can_be_created_after_deletion_with_if_none_match_star(self):
        headers = self.headers.copy()
        headers['If-None-Match'] = '*'
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=headers, status=201)
