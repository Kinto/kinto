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


class ObtainCollectionPermissionTest(PermissionTest):
    def setUp(self):
        super(ObtainCollectionPermissionTest, self).setUp()
        self.permission.add_object_permission_principal('/articles',
                                                        'read',
                                                        'fxa:user')
        self.permission.add_object_permission_principal('/articles',
                                                        'write',
                                                        'fxa:user')
        self.resource.request.path = '/articles'
        self.result = self.resource.collection_get()

    def test_permissions_are_provided_in_collection_get(self):
        self.assertIn('permissions', self.result)

    def test_permissions_are_provided_in_collection_post(self):
        self.resource.request.validated = {'data': {}}
        result = self.resource.collection_post()
        self.assertIn('permissions', result)

    def test_permissions_are_not_provided_in_collection_delete(self):
        result = self.resource.collection_delete()
        self.assertNotIn('permissions', result)

    def test_permissions_gives_lists_of_principals_per_ace(self):
        permissions = self.result['permissions']
        self.assertEqual(permissions['read'], ['fxa:user'])
        self.assertEqual(permissions['write'], ['fxa:user'])


class ObtainRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(ObtainRecordPermissionTest, self).setUp()
        record = self.resource.collection.create_record({})
        record_id = record['id']
        record_uri = '/articles/%s' % record_id
        self.permission.add_object_permission_principal(record_uri,
                                                        'read',
                                                        'fxa:user')
        self.permission.add_object_permission_principal(record_uri,
                                                        'write',
                                                        'fxa:user')
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


class SpecifyCollectionPermissionTest(PermissionTest):
    def setUp(self):
        super(SpecifyCollectionPermissionTest, self).setUp()
        self.resource.request.path = '/articles'

    def test_permissions_can_be_specified_in_collection_post(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.validated = {'data': {}, 'permissions': perms}
        result = self.resource.collection_post()
        self.assertEqual(result['permissions'],
                         {'write': ['jean-louis']})


class SpecifyRecordPermissionTest(PermissionTest):
    def setUp(self):
        super(SpecifyRecordPermissionTest, self).setUp()
        record = self.resource.collection.create_record({})
        record_id = record['id']
        record_uri = '/articles/%s' % record_id
        self.permission.add_object_permission_principal(record_uri,
                                                        'read',
                                                        'fxa:user')
        self.resource.record_id = record_id
        self.resource.request.validated = {'data': {}}
        self.resource.request.path = record_uri

    def test_permissions_are_replaced_with_put(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.validated['permissions'] = perms
        result = self.resource.put()
        self.assertEqual(result['permissions'], perms)

    def test_permissions_are_modified_with_patch(self):
        perms = {'write': ['jean-louis']}
        self.resource.request.validated['permissions'] = perms
        result = self.resource.patch()
        self.assertEqual(result['permissions'],
                         {'write': ['jean-louis'],
                          'read': ['fxa:user']})
