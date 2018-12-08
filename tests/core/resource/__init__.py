import unittest
from unittest import mock

from kinto.core import resource
from kinto.core.authorization import RouteFactory
from kinto.core.storage import memory as storage_memory
from kinto.core.cache import memory as cache_memory
from kinto.core.testing import DummyRequest


class StrictSchema(resource.ResourceSchema):
    class Options:
        preserve_unknown = False


class BaseTest(unittest.TestCase):
    resource_class = resource.Resource

    def setUp(self):
        self.storage = storage_memory.Storage()
        self.cache = cache_memory.Cache(cache_prefix="", cache_max_size_bytes=1000)
        self.resource = self.resource_class(request=self.get_request(), context=self.get_context())
        self.resource.schema = StrictSchema
        self.model = self.resource.model
        self.patch_known_field = mock.patch.object(self.resource, "is_known_field")
        self.validated = {"body": {}, "header": {}, "querystring": {}}
        self.resource.request.validated = self.validated

    def tearDown(self):
        mock.patch.stopall()

    def get_request(self, resource_name=""):
        request = DummyRequest(method="GET")
        request.current_resource_name = resource_name
        request.registry.cache = self.cache
        request.registry.storage = self.storage
        return request

    def get_context(self):
        return RouteFactory(self.get_request())

    @property
    def last_response(self):
        return self.resource.request.response
