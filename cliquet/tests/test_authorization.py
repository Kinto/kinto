import mock

from pyramid.security import Allow
from .support import DummyRequest, unittest
from cliquet.authorization import RouteFactory


class RouteFactoryTest(unittest.TestCase):

    def setUp(self):
        self.record_uri = "/foo/bar"

    def assert_request_resolves_to(self, method, permission, uri=None):
        if uri is None:
            uri = self.record_uri

        request = DummyRequest(method=method)
        request.upath_info = uri
        get_principals = (request.registry.permission.
                          object_permission_authorized_principals)

        get_principals.return_value = [('user', permission), ]
        context = RouteFactory(request)
        get_principals.assert_called_with(uri, permission, None)

        expected_acls = [(Allow, 'user', permission)]
        self.assertEquals(context.__acl__, expected_acls)

    def test_http_get_resolves_in_a_read_permission(self):
        self.assert_request_resolves_to("get", "read")

    def test_http_post_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("post", "create")

    def test_http_delete_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("delete", "write")

    def test_http_post_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("post", "create")

    def test_http_put_unexisting_record_resolves_in_a_create_permission(self):
        self.assert_request_resolves_to("put", "create")

    def test_http_put_existing_record_resolves_in_a_write_permission(self):
        self.assert_request_resolves_to("put", "write")
