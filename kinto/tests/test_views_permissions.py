from .support import (BaseWebTest, unittest, MINIMALIST_RECORD,
                      MINIMALIST_GROUP, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION, get_user_headers)


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

    def get_app_settings(self, additional_settings=None):
        settings = super(PermissionsViewTest, self).get_app_settings(
            additional_settings)
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
