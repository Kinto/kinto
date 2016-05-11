import mock

from cliquet.tests.support import unittest
from cliquet.resource import UserResource, ShareableResource
from cliquet.tests.resource import BaseTest


class ResourceTest(BaseTest):

    def test_get_parent_id_default_to_prefixed_userid(self):
        request = self.get_request()
        parent_id = self.resource.get_parent_id(request)
        self.assertEquals(parent_id, 'basicauth:bob')


class ShareableResourceTest(BaseTest):
    resource_class = ShareableResource

    def test_resource_can_be_created_without_context(self):
        try:
            self.resource_class(self.get_request())
        except Exception as e:
            self.fail(e)

    def test_get_parent_id_is_empty(self):
        request = self.get_request()
        parent_id = self.resource.get_parent_id(request)
        self.assertEquals(parent_id, '')


class NewResource(UserResource):
    def get_parent_id(self, request):
        return "overrided"


class ParentIdOverrideResourceTest(BaseTest):
    resource_class = NewResource

    def test_get_parent_can_be_overridded(self):
        request = self.get_request()

        parent_id = self.resource.get_parent_id(request)
        self.assertEquals(parent_id, 'overrided')
        self.assertEquals(self.resource.model.parent_id, 'overrided')


class DeprecatedBaseResourceTest(unittest.TestCase):

    def setUp(self):
        self.patcher = mock.patch('cliquet.utils.warnings.warn')
        self.addCleanup(self.patcher.stop)

    def test_deprecated_usage_of_base_resource(self):
        mocked = self.patcher.start()
        from cliquet.resource import BaseResource

        class User(BaseResource):
            pass

        error_msg = 'BaseResource is deprecated. Use UserResource instead.'
        mocked.assert_called_with(error_msg, DeprecationWarning, stacklevel=2)
