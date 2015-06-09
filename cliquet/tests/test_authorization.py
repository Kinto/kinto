import mock

from pyramid.security import Allow
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

    def test_http_post_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("post", "create")

    def test_http_put_unexisting_record_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("put", "create", record_not_found=True)

    def test_http_put_existing_record_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("put", "write")

    def test_http_patch_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("patch", "write")


class AuthorizationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.authz = AuthorizationPolicy()
        self.context = mock.MagicMock()
        self.context.object_id = mock.sentinel.object_id
        self.context.required_permission = 'read'
        self.context.get_bound_permissions = mock.sentinel.get_bound_perms
        self.principals = mock.sentinel.principals
        self.permission = 'dynamic'

    def test_permits_refers_to_context_to_check_permissions(self):
        self.context.has_permission.return_value = True
        allowed = self.authz.permits(self.context, self.principals, 'dynamic')
        self.assertTrue(allowed)

    def test_permits_reads_the_context_when_permission_is_dynamic(self):
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.has_permission.assert_called_with(
            mock.sentinel.object_id,
            'read',
            mock.sentinel.principals,
            mock.sentinel.get_bound_perms)

    def test_permits_consider_permission_when_not_dynamic(self):
        self.authz.permits(self.context, self.principals, 'foobar')
        self.context.has_permission.assert_called_with(
            mock.sentinel.object_id,
            'foobar',
            mock.sentinel.principals,
            mock.sentinel.get_bound_perms)

    def test_permits_prepend_obj_type_to_permission_on_create(self):
        self.context.required_permission = 'create'
        self.context.object_type = 'record'
        self.authz.permits(self.context, self.principals, 'dynamic')
        self.context.has_permission.assert_called_with(
            mock.sentinel.object_id,
            'record:create',
            mock.sentinel.principals,
            mock.sentinel.get_bound_perms)
