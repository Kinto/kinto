import mock

from kinto.core.authorization import RouteFactory
from kinto.core.storage import memory
from kinto.tests.core.support import unittest, DummyRequest
from kinto.core.resource import UserResource


class BaseTest(unittest.TestCase):
    resource_class = UserResource

    def setUp(self):
        self.storage = memory.Storage()
        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.model = self.resource.model
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
