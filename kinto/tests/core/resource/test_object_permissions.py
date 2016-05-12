import mock

from pyramid import httpexceptions

from kinto.core.resource import ShareableResource
from kinto.tests.core.resource import BaseTest
from kinto.core.permission.memory import Permission


class PermissionTest(BaseTest):
    resource_class = ShareableResource

    def setUp(self):
        self.permission = Permission()
        super(PermissionTest, self).setUp()

    def get_request(self):
        request = super(PermissionTest, self).get_request()
        request.registry.permission = self.permission
        return request


class CollectionPermissionTest(PermissionTest):
    def setUp(self):
        super(CollectionPermissionTest, self).setUp()
        self.result = self.resource.collection_get()

    def test_permissions_are_not_provided_in_collection_get(self):
        self.assertNotIn('permissions', self.result)

    def test_permissions_are_not_provided_in_collection_delete(self):
        result = self.resource.collection_delete()
        self.assertNotIn('permissions', result)


class ObtainRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(ObtainRecordPermissionTest, self).setUp()
        record = self.resource.model.create_record({})
        record_id = record['id']
        record_uri = '/articles/%s' % record_id
        self.permission.add_principal_to_ace(record_uri, 'read', 'fxa:user')
        self.permission.add_principal_to_ace(record_uri, 'write', 'fxa:user')
        self.resource.record_id = record_id
        self.resource.request.validated = {'data': {}}
        self.resource.request.path = record_uri

    def test_permissions_are_provided_in_record_get(self):
        result = self.resource.get()
        self.assertIn('permissions', result)

    def test_permissions_are_provided_in_record_put(self):
        result = self.resource.put()
        self.assertIn('permissions', result)

    def test_permissions_are_provided_in_record_patch(self):
        result = self.resource.patch()
        self.assertIn('permissions', result)

    def test_permissions_are_not_provided_in_record_delete(self):
        result = self.resource.delete()
        self.assertNotIn('permissions', result)

    def test_permissions_gives_lists_of_principals_per_ace(self):
        result = self.resource.get()
        permissions = result['permissions']
        self.assertEqual(sorted(permissions['read']), ['fxa:user'])
        self.assertEqual(sorted(permissions['write']), ['fxa:user'])


class SpecifyRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(SpecifyRecordPermissionTest, self).setUp()
        self.record = self.resource.model.create_record({})
        record_id = self.record['id']
        self.record_uri = '/articles/%s' % record_id
        self.permission.add_principal_to_ace(self.record_uri,
                                             'read',
                                             'fxa:user')
        self.resource.model.current_principal = 'basicauth:userid'
        self.resource.record_id = record_id
        self.resource.request.validated = {'data': {}}
        self.resource.request.path = self.record_uri

    def test_write_permission_is_given_to_creator_on_post(self):
        self.resource.context.object_uri = '/articles'
        self.resource.request.method = 'POST'
        result = self.resource.collection_post()
        self.assertEqual(sorted(result['permissions']['write']),
                         ['basicauth:userid'])

    def test_write_permission_is_given_to_put(self):
        self.resource.request.method = 'PUT'
        result = self.resource.put()
        permissions = result['permissions']
        self.assertEqual(sorted(permissions['write']), ['basicauth:userid'])

    def test_permissions_can_be_specified_in_collection_post(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.method = 'POST'
        self.resource.context.object_uri = '/articles'
        self.resource.request.validated = {'data': {}, 'permissions': perms}
        result = self.resource.collection_post()
        self.assertEqual(sorted(result['permissions']['write']),
                         ['basicauth:userid', 'jean-louis'])

    def test_permissions_are_replaced_with_put(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.validated['permissions'] = perms
        self.resource.request.method = 'PUT'
        result = self.resource.put()
        # In setUp() 'read' was set on this record.
        # PUT had got rid of it:
        self.assertNotIn('read', result['permissions'])

    def test_permissions_are_modified_with_patch(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.validated = {'permissions': perms}
        self.resource.request.method = 'PATCH'
        result = self.resource.patch()
        permissions = result['permissions']
        self.assertEqual(sorted(permissions['read']), ['fxa:user'])
        self.assertEqual(sorted(permissions['write']),
                         ['basicauth:userid', 'jean-louis'])

    def test_permissions_can_be_removed_with_patch_but_keep_current_user(self):
        self.permission.add_principal_to_ace(self.record_uri,
                                             'write',
                                             'jean-louis')

        perms = {'write': []}
        self.resource.request.validated = {'permissions': perms}
        self.resource.request.method = 'PATCH'
        result = self.resource.patch()
        permissions = result['permissions']
        self.assertEqual(sorted(permissions['read']), ['fxa:user']),
        self.assertEqual(sorted(permissions['write']), ['basicauth:userid'])

    def test_permissions_can_be_removed_with_patch(self):
        self.permission.add_principal_to_ace(self.record_uri,
                                             'write',
                                             'jean-louis')

        perms = {'read': []}
        self.resource.request.validated = {'permissions': perms}
        self.resource.request.method = 'PATCH'
        result = self.resource.patch()
        self.assertNotIn('read', result['permissions'])
        self.assertEqual(sorted(result['permissions']['write']),
                         ['basicauth:userid', 'jean-louis'])

    def test_412_errors_do_not_put_permission_in_record(self):
        self.resource.request.headers['If-Match'] = '"1234567"'  # invalid
        try:
            self.resource.put()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertEqual(error.json['details']['existing'],
                         {'id': self.record['id'],
                          'last_modified': self.record['last_modified']})


class DeletedRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(DeletedRecordPermissionTest, self).setUp()
        record = self.resource.model.create_record({})
        self.resource.record_id = record_id = record['id']
        self.record_uri = '/articles/%s' % record_id
        self.resource.request.route_path.return_value = self.record_uri
        self.resource.request.path = self.record_uri
        self.permission.add_principal_to_ace(self.record_uri,
                                             'read',
                                             'fxa:user')

    def test_permissions_are_deleted_when_record_is_deleted(self):
        self.resource.delete()
        principals = self.permission.object_permission_principals(
            self.record_uri, 'read')
        self.assertEqual(len(principals), 0)

    def test_permissions_are_deleted_when_collection_is_deleted(self):
        self.resource.context.on_collection = True
        self.resource.collection_delete()
        principals = self.permission.object_permission_principals(
            self.record_uri, 'read')
        self.assertEqual(len(principals), 0)


class GuestCollectionListTest(PermissionTest):
    def setUp(self):
        super(GuestCollectionListTest, self).setUp()
        record1 = self.resource.model.create_record({'letter': 'a'})
        record2 = self.resource.model.create_record({'letter': 'b'})
        record3 = self.resource.model.create_record({'letter': 'c'})

        uri1 = '/articles/%s' % record1['id']
        uri2 = '/articles/%s' % record2['id']
        uri3 = '/articles/%s' % record3['id']

        self.permission.add_principal_to_ace(uri1, 'read', 'fxa:user')
        self.permission.add_principal_to_ace(uri2, 'read', 'group')
        self.permission.add_principal_to_ace(uri3, 'read', 'jean-louis')

        self.resource.context.shared_ids = [record1['id'], record2['id']]

    def test_collection_is_filtered_for_current_guest(self):
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 2)

    def test_guest_collection_can_be_filtered(self):
        self.resource.request.GET = {'letter': 'a'}
        with mock.patch.object(self.resource, 'is_known_field'):
            result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)

    def test_guest_collection_is_empty_if_no_record_is_shared(self):
        self.resource.context.shared_ids = ['tata lili']
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 0)

    def test_permission_backend_is_not_queried_if_not_guest(self):
        self.resource.context.shared_ids = []
        self.resource.request.registry.permission = None  # would fail!
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 3)

    def test_unauthorized_error_if_collection_does_not_exist(self):
        pass


class GuestCollectionDeleteTest(PermissionTest):
    def setUp(self):
        super(GuestCollectionDeleteTest, self).setUp()
        record1 = self.resource.model.create_record({'letter': 'a'})
        record2 = self.resource.model.create_record({'letter': 'b'})
        record3 = self.resource.model.create_record({'letter': 'c'})
        record4 = self.resource.model.create_record({'letter': 'd'})

        uri1 = '/articles/%s' % record1['id']
        uri2 = '/articles/%s' % record2['id']
        uri3 = '/articles/%s' % record3['id']
        uri4 = '/articles/%s' % record4['id']

        self.permission.add_principal_to_ace(uri1, 'read', 'fxa:user')
        self.permission.add_principal_to_ace(uri2, 'write', 'fxa:user')
        self.permission.add_principal_to_ace(uri3, 'write', 'group')
        self.permission.add_principal_to_ace(uri4, 'write', 'jean-louis')

        self.resource.context.shared_ids = [record2['id'], record3['id']]
        self.resource.request.method = 'DELETE'

    def get_request(self):
        request = super(GuestCollectionDeleteTest, self).get_request()
        # RouteFactory must be aware of DELETE to query 'write' permission.
        request.method = 'DELETE'
        return request

    def test_collection_is_filtered_for_current_guest(self):
        result = self.resource.collection_delete()
        self.assertEqual(len(result['data']), 2)

    def test_guest_collection_can_be_filtered(self):
        self.resource.request.GET = {'letter': 'b'}
        with mock.patch.object(self.resource, 'is_known_field'):
            result = self.resource.collection_delete()
        self.assertEqual(len(result['data']), 1)
        records, _ = self.resource.model.get_records()
        self.assertEqual(len(records), 3)

    def test_guest_cannot_delete_records_if_not_allowed(self):
        self.resource.context.shared_ids = ['tata lili']
        result = self.resource.collection_delete()
        self.assertEqual(len(result['data']), 0)
        records, _ = self.resource.model.get_records()
        self.assertEqual(len(records), 4)
