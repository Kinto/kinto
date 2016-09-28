import unittest

from kinto.core.testing import get_user_headers

from .support import (BaseWebTest, MINIMALIST_RECORD,
                      MINIMALIST_GROUP, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION)


RECORD_ID = 'd5db6e57-2c10-43e2-96c8-56602ef01435'


class PermissionsViewTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        super(PermissionsViewTest, self).setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/groups/amateurs',
                          MINIMALIST_GROUP,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley/records/' + RECORD_ID,  # noqa
                          MINIMALIST_RECORD,
                          headers=self.headers)

        # Other user.
        self.app.put_json('/buckets/water', MINIMALIST_BUCKET,
                          headers=get_user_headers('alice'))

    def get_app_settings(self, extras=None):
        settings = super(PermissionsViewTest, self).get_app_settings(extras)
        settings['experimental_permissions_endpoint'] = 'True'
        return settings

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
