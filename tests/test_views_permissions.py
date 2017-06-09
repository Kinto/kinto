import unittest

from kinto.core.testing import get_user_headers

from .support import (BaseWebTest, MINIMALIST_RECORD,
                      MINIMALIST_GROUP, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION)


RECORD_ID = 'd5db6e57-2c10-43e2-96c8-56602ef01435'


class PermissionsViewTest(BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['experimental_permissions_endpoint'] = 'True'
        return settings


class EntriesTest(PermissionsViewTest):

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/groups/amateurs',
                          MINIMALIST_GROUP,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley/records/{}'.format(RECORD_ID),
                          MINIMALIST_RECORD,
                          headers=self.headers)

        # Other user.
        self.app.put_json('/buckets/water', MINIMALIST_BUCKET,
                          headers=get_user_headers('alice'))

    def test_permissions_list_entries_for_current_principal(self):
        resp = self.app.get('/permissions', headers=self.headers)
        permissions = resp.json['data']
        self.assertEqual(len(permissions), 4)

    def test_permissions_can_be_listed_anonymously(self):
        self.app.patch_json('/buckets/beers/collections/barley',
                            {'permissions': {'write': ['system.Everyone']}},
                            headers=self.headers)
        resp = self.app.get('/permissions')
        permissions = resp.json['data']
        self.assertEqual(len(permissions), 1)

    def test_implicit_permissions_are_explicited(self):
        resp = self.app.get('/permissions', headers=get_user_headers('alice'))
        permissions = resp.json['data']
        bucket_permissions = permissions[0]
        self.assertEqual(sorted(bucket_permissions['permissions']),
                         ['collection:create',
                          'group:create',
                          'read',
                          'read:attributes',
                          'write'])

    def test_object_details_are_provided(self):
        resp = self.app.get('/permissions', headers=self.headers)
        entries = resp.json['data']
        for entry in entries:
            if entry['resource_name'] == 'record':
                record_permission = entry
        self.assertEqual(record_permission['record_id'], RECORD_ID)
        self.assertEqual(record_permission['collection_id'], 'barley')
        self.assertEqual(record_permission['bucket_id'], 'beers')

    def test_permissions_list_can_be_filtered(self):
        resp = self.app.get('/permissions?in_resource_name=bucket,collection',
                            headers=self.headers)
        permissions = resp.json['data']
        self.assertEqual(len(permissions), 2)

    def test_filtering_with_unknown_field_is_not_supported(self):
        self.app.get('/permissions?movie=bourne',
                     headers=self.headers,
                     status=400)

    def test_permissions_fields_can_be_selected(self):
        resp = self.app.get('/permissions?_fields=uri',
                            headers=self.headers)
        self.assertNotIn('resource_name', resp.json['data'][0])

    def test_permissions_list_can_be_paginated(self):
        resp = self.app.get('/permissions?_limit=2',
                            headers=self.headers)
        self.assertEqual(resp.headers['Total-Records'], '4')
        self.assertIn('Next-Page', resp.headers)
        self.assertEqual(len(resp.json['data']), 2)

    def test_permissions_list_do_not_crash_with_preconditions(self):
        headers = {'If-None-Match': '"123"', **self.headers}
        self.app.get('/permissions', headers=headers)

    def test_permissions_can_be_paginated(self):
        for i in range(10):
            self.app.put_json('/buckets/beers/collections/barley/records/r-{}'.format(i),
                              MINIMALIST_RECORD,
                              headers=self.headers)
        resp = self.app.get('/permissions?resource_name=record&_limit=7', headers=self.headers)
        page1 = resp.json["data"]
        next_page = resp.headers["Next-Page"].replace("http://localhost/v1", "")
        resp = self.app.get(next_page, headers=self.headers)
        page2 = resp.json["data"]
        assert len(page1 + page2) == 11  # see setup().

    def test_permissions_can_be_paginated_with_uri_in_sorting(self):
        for i in range(10):
            self.app.put_json('/buckets/beers/collections/barley/records/r-{}'.format(i),
                              MINIMALIST_RECORD,
                              headers=self.headers)
        resp = self.app.get('/permissions?resource_name=record&_limit=7&_sort=uri',
                            headers=self.headers)
        page1 = resp.json["data"]
        next_page = resp.headers["Next-Page"].replace("http://localhost/v1", "")
        resp = self.app.get(next_page, headers=self.headers)
        page2 = resp.json["data"]
        assert len(page1 + page2) == 11  # see setup().


class GroupsPermissionTest(PermissionsViewTest):

    def setUp(self):
        super().setUp()

        self.admin_headers = get_user_headers('admin')
        self.admin_principal = self.app.get('/', headers=self.admin_headers).json['user']['id']

        self.app.put_json('/buckets/beers',
                          {'permissions': {'write': ['/buckets/beers/groups/admins']}},
                          headers=self.headers)
        self.app.put_json('/buckets/beers/groups/admins',
                          {'data': {'members': [self.admin_principal]}},
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)

        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/groups/admins',
                          {'data': {'members': [self.admin_principal]}},
                          headers=self.headers)
        self.app.put_json('/buckets/sodas/collections/sprite',
                          {'permissions': {'read': ['/buckets/beers/groups/admins']}},
                          headers=self.headers)

    def test_permissions_granted_via_groups_are_listed(self):
        resp = self.app.get('/permissions', headers=self.admin_headers)
        buckets = [e for e in resp.json['data'] if e['resource_name'] == 'bucket']
        self.assertEqual(buckets[0]['id'], 'beers')
        self.assertIn('write', buckets[0]['permissions'])

        collections = [e for e in resp.json['data'] if e['resource_name'] == 'collection']
        self.assertEqual(collections[0]['id'], 'sprite')
        self.assertEqual(collections[0]['bucket_id'], 'sodas')
        self.assertIn('read', collections[0]['permissions'])

    def test_permissions_inherited_are_not_listed(self):
        resp = self.app.get('/permissions', headers=self.admin_headers)
        collections = [e for e in resp.json['data']
                       if e['bucket_id'] == 'beers' and e['resource_name'] == 'collection']
        self.assertEqual(len(collections), 0)


class SettingsPermissionsTest(PermissionsViewTest):

    admin_headers = get_user_headers('admin')
    admin_principal = 'basicauth:bb7fe7b98e759578ef0de85b546dd57d21fe1e399390ad8dafc9886043a00e5c'  # NOQA

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['bucket_write_principals'] = 'system.Authenticated'
        settings['group_create_principals'] = cls.admin_principal
        settings['collection_write_principals'] = 'system.Authenticated'
        settings['record_create_principals'] = '/buckets/beers/groups/admins'
        return settings

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET, headers=self.headers)
        self.app.put_json('/buckets/beers/groups/admins',
                          {'data': {'members': [self.admin_principal]}},
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)

    def test_bucket_write_taken_into_account(self):
        resp = self.app.get('/permissions', headers=get_user_headers("any"))
        buckets = [e for e in resp.json['data'] if e['resource_name'] == 'bucket']
        self.assertEqual(buckets[0]['id'], 'beers')
        self.assertIn('write', buckets[0]['permissions'])

    def test_collection_create_taken_into_account(self):
        resp = self.app.get('/permissions', headers=self.admin_headers)
        buckets = [e for e in resp.json['data'] if e['resource_name'] == 'bucket']
        self.assertEqual(buckets[0]['id'], 'beers')
        self.assertIn('group:create', buckets[0]['permissions'])

    def test_collection_write_taken_into_account(self):
        resp = self.app.get('/permissions', headers=get_user_headers("any"))
        collections = [e for e in resp.json['data'] if e['resource_name'] == 'collection']
        self.assertEqual(collections[0]['id'], 'barley')
        self.assertIn('write', collections[0]['permissions'])

    def test_record_create_taken_into_account(self):
        resp = self.app.get('/permissions', headers=self.admin_headers)
        collections = [e for e in resp.json['data'] if e['resource_name'] == 'collection']
        self.assertEqual(collections[0]['id'], 'barley')
        self.assertIn('record:create', collections[0]['permissions'])

    def test_settings_permissions_are_merged_with_perms_backend(self):
        self.app.patch_json('/buckets/beers',
                            {'permissions': {'collection:create': [self.admin_principal]}},
                            headers=self.headers)
        self.app.patch_json('/buckets/beers/collections/barley',
                            {'permissions': {'read': [self.admin_principal]}},
                            headers=self.headers)

        resp = self.app.get('/permissions', headers=self.admin_headers)

        buckets = [e for e in resp.json['data'] if e['resource_name'] == 'bucket']
        self.assertEqual(buckets[0]['id'], 'beers')
        self.assertIn('group:create', buckets[0]['permissions'])
        self.assertIn('collection:create', buckets[0]['permissions'])

        collections = [e for e in resp.json['data'] if e['resource_name'] == 'collection']
        self.assertEqual(collections[0]['id'], 'barley')
        self.assertIn('record:create', collections[0]['permissions'])
        self.assertIn('read', collections[0]['permissions'])


class DeletedObjectsTest(PermissionsViewTest):

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/groups/admins',
                          MINIMALIST_GROUP,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley/records/vieuxsinge',
                          MINIMALIST_RECORD,
                          headers=self.headers)
        self.app.delete('/buckets/beers', headers=self.headers)

    def test_deleted_objects_are_not_listed(self):
        resp = self.app.get('/permissions', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)
