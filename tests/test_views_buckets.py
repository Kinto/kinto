import unittest

from pyramid.security import Authenticated

from kinto.core.testing import get_user_headers

from .support import (BaseWebTest,
                      MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class BucketViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super().setUp()
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
        bucket = {**MINIMALIST_BUCKET}
        record_url = '/buckets/alexis_beers'
        resp = self.app.put_json(record_url,
                                 bucket,
                                 headers=self.headers)
        self.assertEqual(resp.json['data']['id'], 'alexis_beers')

    def test_can_list_buckets_by_default_since_allowed_to_create(self):
        resp = self.app.get('/buckets',
                            headers=get_user_headers('alice'),
                            status=200)
        assert resp.json['data'] == []

    def test_buckets_name_should_be_simple(self):
        self.app.put_json('/buckets/__beers__',
                          MINIMALIST_BUCKET,
                          headers=self.headers,
                          status=400)

    def test_buckets_should_reject_unaccepted_request_content_type(self):
        headers = {**self.headers, 'Content-Type': 'text/plain'}
        self.app.put('/buckets/beers',
                     MINIMALIST_BUCKET,
                     headers=headers,
                     status=415)

    def test_create_permissions_can_be_added_on_buckets(self):
        bucket = {**MINIMALIST_BUCKET, 'permissions': {'collection:create': ['fxa:user'],
                                                       'group:create': ['fxa:user']}}
        resp = self.app.put_json('/buckets/beers',
                                 bucket,
                                 headers=self.headers,
                                 status=200)
        permissions = resp.json['permissions']
        self.assertIn('fxa:user', permissions['collection:create'])
        self.assertIn('fxa:user', permissions['group:create'])

    def test_wrong_create_permissions_cannot_be_added_on_buckets(self):
        bucket = {**MINIMALIST_BUCKET, 'permissions': {'record:create': ['fxa:user']}}
        self.app.put_json('/buckets/beers',
                          bucket,
                          headers=self.headers,
                          status=400)

    def test_buckets_can_handle_arbitrary_attributes(self):
        public_key = "5866f245a00bb3a39100d31b2f14d453"
        bucket = {**MINIMALIST_BUCKET, 'data': {'public_key': public_key}}
        resp = self.app.put_json('/buckets/beers',
                                 bucket,
                                 headers=self.headers,
                                 status=200)
        data = resp.json['data']
        self.assertIn('public_key', data)
        self.assertEqual(data['public_key'], public_key)

    def test_buckets_can_be_filtered_by_arbitrary_attribute(self):
        bucket = {**MINIMALIST_BUCKET, 'data': {'size': 3}}
        self.app.put_json('/buckets/beers',
                          bucket,
                          headers=self.headers)
        resp = self.app.get('/buckets?min_size=2', headers=self.headers)
        data = resp.json['data']
        self.assertEqual(len(data), 1)


class BucketListTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['bucket_create_principals'] = cls.principal
        return settings

    def test_can_list_buckets_by_default_if_allowed_to_create(self):
        resp = self.app.get('/buckets',
                            headers=self.headers,
                            status=200)
        assert resp.json['data'] == []

    def test_cannot_list_buckets_if_empty_and_not_allowed_to_create(self):
        self.app.get('/buckets', status=401)
        self.app.get('/buckets', headers=get_user_headers('alice'), status=403)

    def test_can_list_buckets_if_some_are_shared(self):
        self.app.put_json('/buckets/whiskies', headers=self.headers)
        self.app.put_json('/buckets/beers',
                          {'permissions': {'write': ['system.Everyone']}},
                          headers=self.headers)

        resp = self.app.get('/buckets', status=200)
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == 'beers'


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
        headers = {**self.headers}
        headers.pop("Content-Type")
        self.app.put('/buckets/catalog', headers=headers)


class BucketReadPermissionTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def setUp(self):
        super().setUp()
        bucket = {**MINIMALIST_BUCKET}
        self.app.put_json(self.record_url,
                          bucket,
                          headers=self.headers)

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        # Give the right to list buckets (for cls.principal and alice).
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
        resp = self.app.post_json(self.collection_url + '/records',
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        record_id = resp.json['data']['id']
        self.previous_ts = resp.headers['ETag']
        self.record_url = self.collection_url + '/records/{}'.format(record_id)
        # Delete the bucket.
        self.app.delete(self.bucket_url, headers=self.headers)

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        # Give the permission to read, to get an explicit 404 once deleted.
        settings['kinto.bucket_read_principals'] = cls.principal
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

    def test_unknown_bucket_raises_404(self):
        resp = self.app.get('/buckets/2', headers=self.headers, status=404)
        self.assertEqual(resp.json['details']['id'], '2')
        self.assertEqual(resp.json['details']['resource_name'], 'bucket')

    def test_buckets_can_be_deleted(self):
        self.app.get(self.bucket_url, headers=self.headers,
                     status=404)

    def test_every_collections_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(self.collection_url, headers=self.headers, status=404)

        # Verify tombstones
        resp = self.app.get('{}/collections?_since=0'.format(self.bucket_url),
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_timestamps_are_refreshed_when_collection_is_recreated(self):
        # Kinto/kinto#1223
        # Recreate with same name.
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        resp = self.app.get(self.collection_url + '/records', headers=self.headers)
        records_ts = resp.headers['ETag']
        self.assertNotEqual(self.previous_ts, records_ts)

    def test_every_groups_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(self.group_url, headers=self.headers, status=404)
        # Verify tombstones
        resp = self.app.get('{}/groups?_since=0'.format(self.bucket_url),
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_every_records_are_deleted_too(self):
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json(self.collection_url, MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.get(self.record_url, headers=self.headers, status=404)

        # Verify tombstones
        resp = self.app.get('{}/records?_since=0'.format(self.collection_url),
                            headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_can_be_created_after_deletion_with_if_none_match_star(self):
        headers = {**self.headers, 'If-None-Match': '*'}
        self.app.put_json(self.bucket_url, MINIMALIST_BUCKET,
                          headers=headers, status=201)

    def test_does_not_delete_buckets_with_similar_names(self):
        self.app.put("/buckets/a", headers=self.headers)
        body = {"permissions": {"read": ["system.Everyone"]}}
        resp = self.app.put_json("/buckets/ab", body, headers=self.headers)
        before = resp.json

        self.app.delete("/buckets/a", headers=self.headers)

        resp = self.app.get("/buckets/ab", headers=self.headers, status=200)
        self.assertEqual(resp.json, before)
