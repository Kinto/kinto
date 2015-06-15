from cliquet.resource import ProtectedResource
from cliquet.tests.resource import BaseTest
from cliquet.permission.memory import Memory


class PermissionTest(BaseTest):
    resource_class = ProtectedResource

    def setUp(self):
        self.permission = Memory()
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
        record = self.resource.collection.create_record({})
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
        self.assertEqual(permissions['read'], ['fxa:user'])
        self.assertEqual(permissions['write'], ['fxa:user'])


class SpecifyRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(SpecifyRecordPermissionTest, self).setUp()
        record = self.resource.collection.create_record({})
        record_id = record['id']
        record_uri = '/articles/%s' % record_id
        self.permission.add_principal_to_ace(record_uri, 'read', 'fxa:user')
        self.resource.record_id = record_id
        self.resource.request.authenticated_userid = 'basic:userid'
        self.resource.request.validated = {'data': {}}
        self.resource.request.path = record_uri

    def test_write_permission_is_given_to_creator_on_post(self):
        self.resource.request.path = '/articles'
        self.resource.request.method = 'POST'
        result = self.resource.collection_post()
        self.assertEqual(result['permissions'], {'write': ['basic:userid']})

    def test_write_permission_is_given_to_put(self):
        self.resource.request.method = 'PUT'
        result = self.resource.put()
        self.assertEqual(result['permissions'],
                         {'read': ['fxa:user'], 'write': ['basic:userid']})

    def test_permissions_can_be_specified_in_collection_post(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.method = 'POST'
        self.resource.request.path = '/articles'
        self.resource.request.validated = {'data': {}, 'permissions': perms}
        result = self.resource.collection_post()
        self.assertEqual(result['permissions'],
                         {'write': ['basic:userid', 'jean-louis']})

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
        self.resource.request.validated['permissions'] = perms
        self.resource.request.method = 'PATCH'
        result = self.resource.patch()
        self.assertEqual(result['permissions'],
                         {'write': ['jean-louis'],
                          'read': ['fxa:user']})


class DeletedRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(DeletedRecordPermissionTest, self).setUp()
        record = self.resource.collection.create_record({})
        self.resource.record_id = record_id = record['id']
        record_uri = '/articles/%s' % record_id
        self.resource.request.path = record_uri
        self.resource.request.route_path.return_value = record_uri
        self.permission.add_principal_to_ace(record_uri, 'read', 'fxa:user')

    def test_permissions_are_deleted_when_record_is_deleted(self):
        record_uri = self.resource.request.path
        self.resource.delete()
        principals = self.permission.object_permission_principals(record_uri,
                                                                  'read')
        self.assertEqual(len(principals), 0)

    def test_permissions_are_deleted_when_collection_is_deleted(self):
        record_uri = self.resource.request.path
        self.resource.request.path = '/articles'
        self.resource.collection_delete()
        principals = self.permission.object_permission_principals(record_uri,
                                                                  'read')
        self.assertEqual(len(principals), 0)
