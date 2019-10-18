import unittest
from unittest import mock

from pyramid import httpexceptions

from kinto.core.resource import Resource, ShareableResource
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.testing import DummyRequest

from . import BaseTest


class ResourceTest(BaseTest):
    def test_raise_if_backend_fails_to_obtain_timestamp(self):
        request = self.get_request()

        with mock.patch.object(
            request.registry.storage,
            "resource_timestamp",
            side_effect=storage_exceptions.BackendError,
        ):
            with self.assertRaises(storage_exceptions.BackendError):
                self.resource_class(request)

    def test_raise_unavailable_if_fail_to_obtain_timestamp_with_readonly(self):
        request = self.get_request()

        excepted_exc = httpexceptions.HTTPServiceUnavailable

        request.registry.settings = {"readonly": "true"}
        with mock.patch.object(
            request.registry.storage,
            "resource_timestamp",
            side_effect=storage_exceptions.BackendError,
        ):
            with self.assertRaises(excepted_exc) as cm:
                self.resource_class(request)
                self.assertIn("writable", cm.exception.message)

    def test_resource_can_be_created_without_context(self):
        try:
            self.resource_class(self.get_request())
        except Exception as e:
            self.fail(e)

    def test_default_parent_id_is_empty(self):
        request = self.get_request()
        parent_id = self.resource.get_parent_id(request)
        self.assertEqual(parent_id, "")


class DeprecatedShareableResource(unittest.TestCase):
    def test_deprecated_warning(self):
        with mock.patch("warnings.warn") as mocked_warnings:
            ShareableResource(context=mock.MagicMock(), request=mock.MagicMock())

        message = "`ShareableResource` is deprecated, use `Resource` instead."
        mocked_warnings.assert_called_with(message, DeprecationWarning)


class DeprecatedMethodsTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        patch = mock.patch("warnings.warn")
        self.mocked_warnings = patch.start()
        self.addCleanup(patch.stop)

        req = DummyRequest()
        req.validated = {"body": {}, "header": {}, "querystring": {}}
        req.registry.storage.list_all.return_value = []
        req.registry.storage.delete_all.return_value = []
        req.registry.storage.create.return_value = {"id": "abc", "last_modified": 123}

        self.resource = Resource(context=mock.MagicMock(), request=req)

    def test_record_id(self):
        self.resource.record_id

        message = "`record_id` is deprecated, use `object_id` instead."
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_process_record(self, *args, **kwargs):
        self.resource.process_record(new={}, old=None)

        message = "`process_record()` is deprecated, use `process_object()` instead."
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_collection_get(self, *args, **kwargs):
        self.resource.collection_get()

        message = "`collection_get()` is deprecated, use `plural_get()` instead."
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_collection_post(self, *args, **kwargs):
        self.resource.collection_post()

        message = "`collection_post()` is deprecated, use `plural_post()` instead."
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_collection_delete(self, *args, **kwargs):
        self.resource.collection_delete()

        message = "`collection_delete()` is deprecated, use `plural_delete()` instead."
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)


class NewResource(Resource):
    def get_parent_id(self, request):
        return "overrided"


class ParentIdOverrideResourceTest(BaseTest):
    resource_class = NewResource

    def test_get_parent_can_be_overridded(self):
        request = self.get_request()

        parent_id = self.resource.get_parent_id(request)
        self.assertEqual(parent_id, "overrided")
        self.assertEqual(self.resource.model.parent_id, "overrided")


class CustomModelResource(Resource):
    def __init__(self, *args, **kwargs):
        self.model = mock.MagicMock()
        self.model.name = mock.sentinel.model
        super().__init__(*args, **kwargs)


class CustomModelResourceTets(unittest.TestCase):
    def test_custom_model_is_not_overriden(self):
        c = CustomModelResource(request=mock.MagicMock())
        self.assertEqual(c.model.name, mock.sentinel.model)
