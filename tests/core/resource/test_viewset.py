from unittest import mock, TestCase

import colander
from cornice.validators import colander_validator
from pyramid import exceptions
from pyramid import testing

from kinto.core import authorization, DEFAULT_SETTINGS
from kinto.core.resource import ViewSet, register_resource
from kinto.core.resource.viewset import PartialSchema, StrictSchema, ShareableViewSet
from kinto.core.testing import unittest


class FakeViewSet(ViewSet):
    """Fake viewset class used for tests."""

    plural_path = "/{resource_name}"
    object_path = "/{resource_name}/{{id}}"

    plural_methods = ("GET",)
    object_methods = ("PUT",)

    def __init__(self):
        self.plural_arguments = self.arguments
        self.object_arguments = self.arguments
        self.update = mock.MagicMock()
        self.responses = mock.MagicMock()

    def arguments(self, resource, method):
        # By default, returns an empty dict of arguments.
        return {}


class FakeResource:
    """Fake resource class used for tests"""

    name = "fake"

    def __init__(self):
        # Create fake views which are in fact mock sentinels.
        # {type}_{method} will map to the sentinel with the same name.
        for endpoint_type in ("plural", "object"):
            for method in ("get", "put", "patch", "delete"):
                if endpoint_type == "object":
                    view_name = method
                else:
                    view_name = "_".join((endpoint_type, method))
                setattr(self, view_name, getattr(mock.sentinel, view_name))


class ViewSetTest(unittest.TestCase):
    def test_arguments_are_merged_on_initialization(self):
        viewset = ViewSet(plural_path=mock.sentinel.plural_path)
        self.assertEqual(viewset.plural_path, mock.sentinel.plural_path)

    def test_default_arguments_are_copied_before_being_returned(self):
        original_arguments = {}
        viewset = ViewSet(plural_get_arguments=original_arguments)
        viewset.responses = mock.MagicMock()
        arguments = viewset.plural_arguments(mock.MagicMock(), "GET")
        self.assertEqual(original_arguments, {})
        self.assertNotEqual(original_arguments, arguments)

    def test_schema_is_added_when_method_matches(self):
        viewset = ViewSet()
        viewset.responses = mock.MagicMock()
        resource = mock.MagicMock()
        arguments = viewset.plural_arguments(resource, "GET")
        self.assertIn("schema", arguments)

    def test_schema_is_added_when_uppercase_method_matches(self):
        viewset = ViewSet(plural_methods=("GET", "DELETE"))
        viewset.responses = mock.MagicMock()
        arguments = viewset.plural_arguments(mock.MagicMock(), "get")
        self.assertIn("schema", arguments)

    @mock.patch("kinto.core.resource.viewset.RequestSchema")
    def test_a_default_schema_is_added_when_method_doesnt_match(self, mocked):
        viewset = ViewSet()
        resource = mock.MagicMock()
        viewset.responses = mock.MagicMock()
        mocked.Mapping.return_value = mock.sentinel.default_schema

        arguments = viewset.plural_arguments(resource, "GET")
        self.assertNotEqual(arguments["schema"], resource.schema)

        mocked.assert_called_with()

    @mock.patch("kinto.core.resource.viewset.RequestSchema")
    def test_class_parameters_are_used_for_plural_arguments(self, mocked):
        default_arguments = {"cors_headers": mock.sentinel.cors_headers}

        default_get_arguments = {"accept": mock.sentinel.accept}

        default_plural_arguments = {"cors_origins": mock.sentinel.cors_origins}

        plural_get_arguments = {"error_handler": mock.sentinel.error_handler}

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_get_arguments=default_get_arguments,
            default_plural_arguments=default_plural_arguments,
            plural_get_arguments=plural_get_arguments,
        )

        viewset.responses = mock.MagicMock()
        arguments = viewset.plural_arguments(mock.MagicMock(), "get")

        self.assertDictEqual(
            arguments,
            {
                "schema": mocked().bind(),
                "accept": mock.sentinel.accept,
                "cors_headers": mock.sentinel.cors_headers,
                "cors_origins": mock.sentinel.cors_origins,
                "error_handler": mock.sentinel.error_handler,
                "validators": [colander_validator],
                "response_schemas": viewset.responses.get_and_bind(),
            },
        )

    @mock.patch("kinto.core.resource.viewset.RequestSchema")
    def test_default_arguments_are_used_for_object_arguments(self, mocked):
        default_arguments = {"cors_headers": mock.sentinel.cors_headers}

        default_get_arguments = {"accept": mock.sentinel.accept}

        default_object_arguments = {"cors_origins": mock.sentinel.object_cors_origins}

        object_get_arguments = {"error_handler": mock.sentinel.error_handler}

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_get_arguments=default_get_arguments,
            default_object_arguments=default_object_arguments,
            object_get_arguments=object_get_arguments,
        )

        viewset.responses = mock.MagicMock()
        arguments = viewset.object_arguments(mock.MagicMock(), "get")

        self.assertDictEqual(
            arguments,
            {
                "schema": mocked().bind(),
                "accept": mock.sentinel.accept,
                "cors_headers": mock.sentinel.cors_headers,
                "cors_origins": mock.sentinel.object_cors_origins,
                "error_handler": mock.sentinel.error_handler,
                "validators": [colander_validator],
                "response_schemas": viewset.responses.get_and_bind(),
            },
        )

    @mock.patch("kinto.core.resource.viewset.RequestSchema")
    def test_class_parameters_overwrite_each_others(self, mocked):
        # Some class parameters should overwrite each others.
        # The more specifics should prevail over the more generics.
        # Items annoted with a "<<" are the one that should prevail.
        default_arguments = {
            "cors_origins": mock.sentinel.default_cors_origins,
            "error_handler": mock.sentinel.default_error_handler,
            "cors_headers": mock.sentinel.default_cors_headers,  # <<
        }
        default_object_arguments = {
            "cors_origins": mock.sentinel.default_object_cors_origin,
            "error_handler": mock.sentinel.default_object_error_handler,  # <<
        }

        object_get_arguments = {"cors_origins": mock.sentinel.object_get_cors_origin}  # <<

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_object_arguments=default_object_arguments,
            object_get_arguments=object_get_arguments,
        )

        viewset.responses = mock.MagicMock()
        arguments = viewset.object_arguments(mock.MagicMock(), "get")

        self.assertDictEqual(
            arguments,
            {
                "schema": mocked().bind(),
                "cors_headers": mock.sentinel.default_cors_headers,
                "error_handler": mock.sentinel.default_object_error_handler,
                "cors_origins": mock.sentinel.object_get_cors_origin,
                "validators": [colander_validator],
                "response_schemas": viewset.responses.get_and_bind(),
            },
        )

    @mock.patch("kinto.core.resource.viewset.RequestSchema")
    def test_service_arguments_arent_inherited_by_object_arguments(self, mocked):
        service_arguments = {"description": "The little book of calm"}

        default_arguments = {"cors_headers": mock.sentinel.cors_headers}
        viewset = ViewSet(
            default_arguments=default_arguments,
            service_arguments=service_arguments,
            default_object_arguments={},
            object_get_arguments={},
        )

        viewset.responses = mock.MagicMock()
        arguments = viewset.object_arguments(mock.MagicMock(), "get")

        self.assertDictEqual(
            arguments,
            {
                "schema": mocked().bind(),
                "cors_headers": mock.sentinel.cors_headers,
                "validators": [colander_validator],
                "response_schemas": viewset.responses.get_and_bind(),
            },
        )

    def test_get_service_name_returns_the_viewset_name_if_defined(self):
        viewset = ViewSet(name="fakename")
        self.assertEqual(viewset.get_service_name("object", mock.MagicMock), "fakename-object")

    def test_get_service_name_returns_resource_att_if_not_callable(self):
        viewset = ViewSet()
        resource = mock.MagicMock()
        resource.name = "fakename"
        self.assertEqual(viewset.get_service_name("object", resource), "fakename-object")

    def test_get_service_name_doesnt_use_callable_as_a_name(self):
        viewset = ViewSet()
        resource = mock.MagicMock()
        resource.name = lambda x: "should not be called"
        resource.__name__ = "FakeName"
        self.assertEqual(viewset.get_service_name("object", resource), "fakename-object")

    def test_is_endpoint_enabled_returns_true_if_unknown(self):
        viewset = ViewSet()
        config = {}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "get", config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_false_if_disabled(self):
        viewset = ViewSet()
        config = {"object_fake_get_enabled": False}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "get", config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_true_if_enabled(self):
        viewset = ViewSet()
        config = {"object_fake_get_enabled": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "get", config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_put_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "put", config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_post_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "post", config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_patch_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "patch", config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_delete_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "delete", config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_true_for_get_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "get", config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_true_for_options_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "options", config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_true_for_head_if_readonly(self):
        viewset = ViewSet()
        config = {"readonly": True}
        is_enabled = viewset.is_endpoint_enabled("object", "fake", "head", config)
        self.assertTrue(is_enabled)

    def test_permission_dynamic_is_set_by_default(self):
        viewset = ViewSet()
        viewset.responses = mock.MagicMock()
        resource = mock.MagicMock()
        args = viewset.plural_arguments(resource, "GET")
        self.assertEqual(args["permission"], "dynamic")

    def test_get_service_arguments_has_default_factory(self):
        viewset = ViewSet()
        args = viewset.get_service_arguments()
        self.assertEqual(args["factory"], authorization.RouteFactory)


class TestViewsetBoundSchemas(unittest.TestCase):
    def setUp(self):
        self.viewset = ViewSet()
        self.viewset.responses = mock.MagicMock()
        self.resource = mock.MagicMock()

    def test_request_schemas_have_header_and_querystring(self):
        self.viewset = ViewSet(
            default_get_arguments={}, default_object_arguments={}, object_get_arguments={}
        )
        arguments = self.viewset.object_arguments(self.resource, "GET")
        schema = arguments["schema"]
        self.assertIn("querystring", schema)
        self.assertIn("header", schema)

    def test_payload_request_schemas_have_a_body(self):
        arguments = self.viewset.object_arguments(self.resource, "PUT")
        schema = arguments["schema"]
        self.assertIn("body", schema)

    def test_plural_deserialize_sort(self):
        arguments = self.viewset.plural_arguments(self.resource, "DELETE")
        schema = arguments["schema"]
        value = {"querystring": {"_sort": "foo,-bar"}}
        deserialized = schema.deserialize(value)
        expected = {"querystring": {"_sort": ["foo", "-bar"]}}
        self.assertEqual(deserialized, expected)

    def test_plural_get_deserialize_fields(self):
        arguments = self.viewset.plural_arguments(self.resource, "GET")
        schema = arguments["schema"]
        value = {"querystring": {"_fields": "foo,bar"}}
        deserialized = schema.deserialize(value)
        expected = {"querystring": {"_fields": ["foo", "bar"]}}
        self.assertEqual(deserialized, expected)

    def test_get_object_deserialize_fields(self):
        arguments = self.viewset.object_arguments(self.resource, "GET")
        schema = arguments["schema"]
        value = {"querystring": {"_fields": "foo,bar"}}
        deserialized = schema.deserialize(value)
        expected = {"querystring": {"_fields": ["foo", "bar"]}}
        self.assertEqual(deserialized, expected)

    def test_patch_object_validate_response_behavior(self):
        arguments = self.viewset.plural_arguments(self.resource, "PATCH")
        schema = arguments["schema"]
        invalid = {"header": {"Response-Behavior": "impolite"}}
        self.assertRaises(colander.Invalid, schema.deserialize, invalid)


class TestViewsetSchemasTest(unittest.TestCase):
    def test_partial_schema_ignores_unknown(self):
        schema = PartialSchema()
        result = schema.deserialize({"foo": "bar"})
        self.assertEqual(result, {})

    def test_strict_schema_raise_on_unknown(self):
        schema = StrictSchema()
        self.assertRaises(colander.Invalid, schema.deserialize, {"foo": "bar"})


class RegisterTest(unittest.TestCase):
    def setUp(self):
        self.resource = FakeResource
        self.viewset = FakeViewSet()

    @mock.patch("kinto.core.resource.Service")
    def test_register_fails_if_no_storage_backend_is_configured(self, *args):
        venusian_callback = register_resource(self.resource, viewset=self.viewset)
        context = mock.MagicMock()
        config = testing.setUp(settings=DEFAULT_SETTINGS)
        context.config.with_package.return_value = config
        try:
            venusian_callback(context, None, None)
        except exceptions.ConfigurationError as e:
            error = e
        self.assertIn("storage backend is missing", str(error))

    @mock.patch("kinto.core.resource.Service")
    def test_viewset_is_updated_if_provided(self, service_class):
        additional_params = {"foo": "bar"}
        register_resource(self.resource, viewset=self.viewset, **additional_params)
        self.viewset.update.assert_called_with(**additional_params)

    def test_resource_default_viewset_is_used_if_not_provided(self):
        resource = FakeResource
        resource.default_viewset = mock.Mock()
        additional_params = {"foo": "bar"}
        register_resource(resource, **additional_params)
        resource.default_viewset.assert_called_with(**additional_params)

    @mock.patch("kinto.core.resource.Service")
    def test_plural_views_are_registered_in_cornice(self, service_class):
        venusian_callback = register_resource(self.resource, viewset=self.viewset)

        config = mock.MagicMock()
        config.registry.settings = DEFAULT_SETTINGS

        context = mock.MagicMock()
        context.config.with_package.return_value = config
        venusian_callback(context, None, None)

        service_class.assert_any_call(
            "fake-plural", "/fake", depth=1, **self.viewset.get_service_arguments()
        )
        service_class().add_view.assert_any_call("GET", "plural_get", klass=self.resource)

    @mock.patch("kinto.core.resource.Service")
    def test_object_views_are_registered_in_cornice(self, service_class):
        venusian_callback = register_resource(self.resource, viewset=self.viewset)

        config = mock.MagicMock()
        config.registry.settings = DEFAULT_SETTINGS

        context = mock.MagicMock()
        context.config.with_package.return_value = config
        venusian_callback(context, None, None)

        service_class.assert_any_call(
            "fake-object", "/fake/{id}", depth=1, **self.viewset.get_service_arguments()
        )
        service_class().add_view.assert_any_call("PUT", "put", klass=self.resource)

    @mock.patch("kinto.core.resource.Service")
    def test_plural_methods_are_skipped_if_not_enabled(self, service_cls):
        venusian_callback = register_resource(self.resource, viewset=self.viewset)

        context = mock.MagicMock()
        context.registry.settings = {"object_fake_put_enabled": False}
        context.config.with_package.return_value = context
        venusian_callback(context, None, None)

        # Only the plural views should have been added.
        # 3 calls: two registering the service classes,
        # one for the plural_get
        self.assertEqual(len(service_cls.mock_calls), 3)
        service_cls.assert_any_call(
            "fake-plural", "/fake", depth=1, **self.viewset.get_service_arguments()
        )
        service_cls().add_view.assert_any_call("GET", "plural_get", klass=self.resource)

    @mock.patch("kinto.core.resource.Service")
    def test_object_methods_are_skipped_if_not_enabled(self, service_class):
        venusian_callback = register_resource(self.resource, viewset=self.viewset)

        context = mock.MagicMock()
        context.config.with_package.return_value = context
        context.registry.settings = {"plural_fake_get_enabled": False}
        venusian_callback(context, None, None)

        # Only the plural views should have been added.
        # 3 calls: two registering the service classes,
        # one for the plural_get
        self.assertEqual(len(service_class.mock_calls), 3)
        service_class.assert_any_call(
            "fake-object", "/fake/{id}", depth=1, **self.viewset.get_service_arguments()
        )
        service_class().add_view.assert_any_call("PUT", "put", klass=self.resource)

    @mock.patch("kinto.core.resource.Service")
    def test_endpoint_is_skipped_if_object_path_is_none(self, service_cls):
        self.viewset.object_path = None

        venusian_callback = register_resource(self.resource, viewset=self.viewset)
        config = mock.MagicMock()
        config.registry.settings = DEFAULT_SETTINGS
        context = mock.MagicMock()
        context.config.with_package.return_value = config
        venusian_callback(context, None, None)

        paths = [call[1][1] for call in service_cls.mock_calls]
        self.assertIn("/fake", paths)
        self.assertNotIn("/fake/{id}", paths)


class DeprecatedShareableViewset(TestCase):
    def test_deprecated_warning(self):
        with mock.patch("warnings.warn") as mocked_warnings:
            ShareableViewSet()

        message = "`ShareableViewSet` is deprecated, use `ViewSet` instead."
        mocked_warnings.assert_called_with(message, DeprecationWarning)
