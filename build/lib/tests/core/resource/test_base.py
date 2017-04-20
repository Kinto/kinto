import mock
from pyramid import httpexceptions

from kinto.core.resource import UserResource, ShareableResource
from kinto.core.storage import exceptions as storage_exceptions

from . import BaseTest


class ResourceTest(BaseTest):

    def test_get_parent_id_default_to_prefixed_userid(self):
        request = self.get_request()
        parent_id = self.resource.get_parent_id(request)
        self.assertEquals(parent_id, 'basicauth:bob')

    def test_raise_if_backend_fails_to_obtain_timestamp(self):
        request = self.get_request()

        with mock.patch.object(request.registry.storage,
                               'collection_timestamp',
                               side_effect=storage_exceptions.BackendError):
            with self.assertRaises(storage_exceptions.BackendError):
                self.resource_class(request)

    def test_raise_unavailable_if_fail_to_obtain_timestamp_with_readonly(self):
        request = self.get_request()

        excepted_exc = httpexceptions.HTTPServiceUnavailable

        request.registry.settings = {'readonly': 'true'}
        with mock.patch.object(request.registry.storage,
                               'collection_timestamp',
                               side_effect=storage_exceptions.BackendError):
            with self.assertRaises(excepted_exc) as cm:
                self.resource_class(request)
                self.assertIn('writable', cm.exception.message)


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
