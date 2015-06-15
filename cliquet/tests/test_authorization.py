import mock

from pyramid.request import Request

from .support import DummyRequest, unittest
from cliquet.authorization import RouteFactory, AuthorizationPolicy
from cliquet.storage import exceptions as storage_exceptions


class RouteFactoryTest(unittest.TestCase):

    def setUp(self):
        self.record_uri = "/foo/bar"

    def assert_request_resolves_to(self, method, permission, uri=None,
                                   record_not_found=False):
        if uri is None:
            uri = self.record_uri

        with mock.patch('cliquet.utils.current_service') as current_service:
            # Patch current service.
            resource = mock.MagicMock()
            resource.record_id = 1
            if record_not_found:
                resource.collection.get_record.side_effect = \
                    storage_exceptions.RecordNotFoundError
            else:
                resource.collection.get_record.return_value = 1
            current_service().resource.return_value = resource

            # Do the actual call.
            request = DummyRequest(method=method)
            request.upath_info = uri
            context = RouteFactory(request)

            self.assertEquals(context.required_permission, permission)

    def test_http_get_resolves_in_a_read_permission(self):
        self.assert_request_resolves_to("get", "read")

    def test_http_post_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("post", "create")

    def test_http_delete_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("delete", "write")

    def test_http_put_unexisting_record_resolves_in_a_create_permission(self):
        with mock.patch('cliquet.utils.current_service') as current_service:
            # Patch current service.
            resource = mock.MagicMock()
            resource.record_id = 1
            resource.collection.get_record.side_effect = \
                storage_exceptions.RecordNotFoundError
            current_service().resource.return_value = resource
            current_service().collection_path = '/buckets/{bucket_id}'
            # Do the actual call.
            request = DummyRequest(method='put')
            request.upath_info = '/buckets/abc/collections/1'
            request.matchdict = {'bucket_id': 'abc'}
            context = RouteFactory(request)

            self.assertEquals(context.object_id, '/buckets/abc')
            self.assertEquals(context.required_permission, 'create')

    def test_http_put_existing_record_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("put", "write")

    def test_http_patch_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("patch", "write")

    def test_attributes_are_none_with_blank_requests(self):
        request = Request.blank(path='/')
        request.registry = mock.Mock(settings={})
        context = RouteFactory(request)
        self.assertIsNone(context.object_id)
        self.assertIsNone(context.required_permission)
        self.assertIsNone(context.resource_name)
        self.assertIsNone(context.check_permission)

    def test_attributes_are_none_with_non_resource_requests(self):
        basic_service = object()
        request = Request.blank(path='/')
        request.matched_route = mock.Mock(pattern='foo')
        request.registry = mock.Mock(cornice_services={'foo': basic_service})
        request.registry.settings = {}

        context = RouteFactory(request)
        self.assertIsNone(context.object_id)
        self.assertIsNone(context.required_permission)
        self.assertIsNone(context.resource_name)
        self.assertIsNone(context.check_permission)

    def test_route_factory_adds_allowed_principals_from_settings(self):
        with mock.patch('cliquet.utils.current_service') as current_service:
            # Patch current service.
            resource = mock.MagicMock()
            current_service().resource.return_value = resource
            current_service().collection_path = '/buckets'
            current_service().viewset.get_name.return_value = 'bucket'
            # Do the actual call.
            request = DummyRequest(method='post')
            request.upath_info = '/buckets'
            request.matchdict = {}
            request.registry = mock.Mock()
            request.registry.settings = {
                'cliquet.bucket_create_principals': 'fxa:user'
            }
            context = RouteFactory(request)

            self.assertEquals(context.allowed_principals, ['fxa:user'])


class AuthorizationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.authz = AuthorizationPolicy()
        self.authz.get_bound_permissions = mock.sentinel.get_bound_perms
        self.context = mock.MagicMock()
        self.context.allowed_principals = []
        self.context.object_id = mock.sentinel.object_id
        self.context.required_permission = 'read'
        self.principals = []
        self.permission = 'dynamic'

    def test_permits_refers_to_context_to_check_permissions(self):
        self.context.check_permission.return_value = True
        allowed = self.authz.permits(self.context, self.principals, 'dynamic')
        self.assertTrue(allowed)

    def test_permits_refers_to_context_to_check_permission_principals(self):
        self.context.check_permission.return_value = False
        self.context.allowed_principals = ['fxa:user']
        allowed = self.authz.permits(
            self.context, ['fxa:user', 'system.Authenticated'], 'dynamic')
        self.assertTrue(allowed)

    def test_permits_reads_the_context_when_permission_is_dynamic(self):
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.check_permission.assert_called_with(
            'read',
            self.principals,
            get_bound_permissions=mock.sentinel.get_bound_perms)

    def test_permits_consider_permission_when_not_dynamic(self):
        self.authz.permits(self.context, self.principals, 'foobar')
        self.context.check_permission.assert_called_with(
            'foobar',
            self.principals,
            get_bound_permissions=mock.sentinel.get_bound_perms)

    def test_permits_prepend_obj_type_to_permission_on_create(self):
        self.context.required_permission = 'create'
        self.context.resource_name = 'record'
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.check_permission.assert_called_with(
            'record:create',
            self.principals,
            get_bound_permissions=mock.sentinel.get_bound_perms)

    def test_permits_takes_route_factory_allowed_principals_into_account(self):
        self.context.resource_name = 'record'
        self.context.required_permission = 'create'
        self.allowed_principals = ['fxa:user']
        has_permission = self.authz.permits(
            self.context, ['fxa:user'], 'dynamic')
        self.context.check_permission.assert_not_called()
        self.assertTrue(has_permission)
