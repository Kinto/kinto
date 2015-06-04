import mock

from .support import DummyRequest, unittest
from cliquet.authorization import RouteFactory


class RouteFactoryTest(unittest.TestCase):

    def test_http_get_resolves_in_a_read_permission(self):
        request = DummyRequest(method="get")
        get_principals = (request.registry.permission.
                          object_permission_authorized_principals)
        RouteFactory(request)
        get_principals.assert_called_with()

    def test_http_post_resolves_in_a_create_permission(self):
        pass

    def test_http_delete_resolves_in_a_write_permission(self):
        pass

    def test_http_post_resolves_in_a_create_permission(self):
        pass

    def test_http_put_unexisting_record_resolves_in_a_create_permission(self):
        pass

    def test_http_put_existing_record_resolves_in_a_write_permission(self):
        pass
