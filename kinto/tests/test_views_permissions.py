from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)
from cliquet.tests.support import authorize


class PermissionsTest(BaseWebTest, unittest.TestCase):

    def get_app_settings(self, additional_settings=None):
        extra = {
            'multiauth.authorization_policy':
                'kinto.tests.support.AllowAuthorizationPolicy'
        }
        extra.update(additional_settings or {})
        return super(PermissionsTest, self).get_app_settings(
            additional_settings=extra)


class BucketPermissionsTest(PermissionsTest):

    def test_creation_is_allowed_to_authenticated_by_default(self):
        self.app.put_json('/buckets/beer',
                          MINIMALIST_BUCKET,
                          headers=self.headers)


class CollectionPermissionsTest(PermissionsTest):

    def setUp(self):
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'write': [self.principal]}
        self.app.put_json('/buckets/beer',
                          bucket,
                          headers=self.headers)

    def test_creation_is_allowed_if_write_on_bucket(self):
        self.app.put_json('/buckets/beer/collections/barley',
                          MINIMALIST_BUCKET,
                          headers=self.headers)

    def test_creation_is_forbidden_is_no_write_on_bucket(self):
        headers = self.headers.copy()
        headers.update(**get_user_headers('alice'))
        self.app.put_json('/buckets/beer/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=headers,
                          status=403)

    # def test_current_user_receives_write_permission_on_creation(self):
    #     resp = self.app.put_json('/buckets/beer',
    #                              MINIMALIST_BUCKET,
    #                              headers=self.headers)
    #     permissions = resp.json['permissions']
    #     self.assertIn(self.userid, permissions['write'])
