import mock

from cliquet.authorization import RouteFactory
from cliquet.storage import memory
from cliquet.tests.support import unittest, DummyRequest
from cliquet.resource import BaseResource, ProtectedResource


class BaseTest(unittest.TestCase):
    resource_class = BaseResource

    def setUp(self):
        self.storage = memory.Memory()
        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.collection = self.resource.collection
        self.patch_known_field = mock.patch.object(self.resource,
                                                   'is_known_field')

    def tearDown(self):
        mock.patch.stopall()

    def get_request(self):
        request = DummyRequest(method='GET')
        request.registry.storage = self.storage
        return request

    def get_context(self):
        return RouteFactory(self.get_request())

    @property
    def last_response(self):
        return self.resource.request.response


class ProtectedResourceTest(BaseTest):
    resource_class = ProtectedResource

    def test_resource_can_be_created_without_context(self):
        try:
            ProtectedResource(self.get_request())
        except Exception as e:
            self.fail(e)


class ParentIdResourceTest(BaseTest):

    def test_get_parent_id_default_to_prefixed_userid(self):
        request = self.get_request()
        parent_id = self.resource.get_parent_id(request)
        self.assertEquals(parent_id, 'basicauth:bob')


class NewResource(BaseResource):
    def get_parent_id(self, request):
        return "overrided"


class ParentIdOverrideResourceTest(BaseTest):
    resource_class = NewResource

    def test_get_parent_can_be_overridded(self):
        request = self.get_request()

        parent_id = self.resource.get_parent_id(request)
        self.assertEquals(parent_id, 'overrided')
        self.assertEquals(self.resource.collection.parent_id, 'overrided')
