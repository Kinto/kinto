from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_COLLECTION,
                      MINIMALIST_GROUP, MINIMALIST_RECORD)


class PermissionsTest(BaseWebTest, unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(PermissionsTest, self).__init__(*args, **kwargs)
        self.alice_headers = self.headers.copy()
        self.alice_headers.update(**get_user_headers('alice'))
        self.alice_principal = ('basicauth:8df4b22019cc89d0bb679bc51373a9da56a'
                                '7ae9978c52fbe684510c3d257c855')
        self.bob_headers = self.headers.copy()
        self.bob_headers.update(**get_user_headers('bob'))
        self.bob_principal = ('basicauth:21364d1282b58b3af15a0d619d03122a318be'
                              'e30c1a5a2d09c3b958e5f7fb71a')


class BucketPermissionsTest(PermissionsTest):

    def setUp(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'read': [self.alice_principal]}
        self.app.put_json('/buckets/sodas',
                          bucket,
                          headers=self.headers)

    def test_creation_is_allowed_to_authenticated_by_default(self):
        self.app.put_json('/buckets/beer',
                          MINIMALIST_BUCKET,
                          headers=self.headers)

    def test_current_user_receives_write_permission_on_creation(self):
        resp = self.app.put_json('/buckets/beer',
                                 MINIMALIST_BUCKET,
                                 headers=self.headers)
        permissions = resp.json['permissions']
        self.assertIn(self.principal, permissions['write'])

    def test_can_read_if_allowed(self):
        self.app.get('/buckets/sodas',
                     headers=self.alice_headers)

    def test_cannot_write_if_not_allowed(self):
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.alice_headers,
                          status=403)


class CollectionPermissionsTest(PermissionsTest):

    def setUp(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {
            'read': [self.alice_principal],
            'write': [self.bob_principal]
        }
        self.app.put_json('/buckets/beer',
                          bucket,
                          headers=self.headers)
        self.app.put_json('/buckets/beer/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)

    def test_read_is_allowed_if_read_on_bucket(self):
        self.app.get('/buckets/beer/collections/barley',
                     headers=self.alice_headers)

    def test_read_is_allowed_if_write_on_bucket(self):
        self.app.get('/buckets/beer/collections/barley',
                     headers=self.bob_headers)

    def test_cannot_read_if_not_allowed(self):
        headers = self.headers.copy()
        headers.update(**get_user_headers('jean-louis'))
        self.app.get('/buckets/beer/collections/barley',
                     headers=headers,
                     status=403)

    def test_cannot_write_if_not_allowed(self):
        self.app.put_json('/buckets/beer/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.alice_headers,
                          status=403)


class GroupPermissionsTest(PermissionsTest):

    def setUp(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {
            'read': [self.alice_principal],
            'write': [self.bob_principal]
        }
        self.app.put_json('/buckets/beer',
                          bucket,
                          headers=self.headers)

        self.app.put_json('/buckets/beer/groups/moderators',
                          MINIMALIST_GROUP,
                          headers=self.headers)

    def test_creation_is_allowed_if_write_on_bucket(self):
        self.app.post_json('/buckets/beer/groups',
                           MINIMALIST_GROUP,
                           headers=self.headers)

    def test_read_is_allowed_if_read_on_bucket(self):
        self.app.get('/buckets/beer/groups/moderators',
                     headers=self.alice_headers)

    def test_read_is_allowed_if_write_on_bucket(self):
        self.app.get('/buckets/beer/groups/moderators',
                     headers=self.bob_headers)

    def test_cannot_read_if_not_allowed(self):
        headers = self.headers.copy()
        headers.update(**get_user_headers('jean-louis'))
        self.app.get('/buckets/beer/groups/moderators',
                     headers=headers,
                     status=403)

    def test_cannot_write_if_not_allowed(self):
        self.app.put_json('/buckets/beer/groups/moderators',
                          MINIMALIST_GROUP,
                          headers=self.alice_headers,
                          status=403)

    def test_creation_is_forbidden_is_no_write_on_bucket(self):
        self.app.post_json('/buckets/beer/groups',
                           MINIMALIST_GROUP,
                           headers=self.alice_headers,
                           status=403)


class RecordPermissionsTest(PermissionsTest):

    def setUp(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'write': [self.alice_principal]}
        self.app.put_json('/buckets/beer',
                          bucket,
                          headers=self.headers)

        collection = MINIMALIST_COLLECTION.copy()
        collection['permissions'] = {'write': [self.bob_principal]}
        self.app.put_json('/buckets/beer/collections/barley',
                          collection,
                          headers=self.headers)

    def test_creation_is_allowed_if_write_on_bucket(self):
        self.app.post_json('/buckets/beer/collections/barley/records',
                           MINIMALIST_RECORD,
                           headers=self.alice_headers)

    def test_creation_is_allowed_if_write_on_collection(self):
        self.app.post_json('/buckets/beer/collections/barley/records',
                           MINIMALIST_RECORD,
                           headers=self.bob_headers)

    def test_creation_is_forbidden_is_no_write_on_bucket_nor_collection(self):
        headers = self.headers.copy()
        headers.update(**get_user_headers('jean-louis'))
        self.app.post_json('/buckets/beer/collections/barley/records',
                           MINIMALIST_RECORD,
                           headers=headers,
                           status=403)

    def test_record_permissions_are_modified_by_patch(self):
        collection_url = '/buckets/beer/collections/barley/records'
        resp = self.app.post_json(collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        record = resp.json['data']
        resp = self.app.patch_json(collection_url + '/' + record['id'],
                                   {'permissions': {'read': ['fxa:user']}},
                                   headers=self.headers)
        self.assertIn('fxa:user', resp.json['permissions']['read'])
