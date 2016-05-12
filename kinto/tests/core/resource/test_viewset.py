import colander
import mock
from pyramid import exceptions
from pyramid import testing

from kinto.core import authorization, DEFAULT_SETTINGS
from kinto.core.resource import ViewSet, ShareableViewSet, register_resource
from kinto.tests.core.support import unittest


class FakeViewSet(ViewSet):
    """Fake viewset class used for tests."""
    collection_path = "/{resource_name}"
    record_path = "/{resource_name}/{{id}}"

    collection_methods = ('GET',)
    record_methods = ('PUT',)

    def __init__(self):
        self.collection_arguments = self.arguments
        self.record_arguments = self.arguments
        self.update = mock.MagicMock()

    def arguments(self, resource, method):
        # By default, returns an empty dict of arguments.
        return {}


class FakeResource(object):
    """Fake resource class used for tests"""
    name = "fake"

    def __init__(self):
        # Create fake views which are in fact mock sentinels.
        # {type}_{method} will map to the sentinel with the same name.
        for endpoint_type in ('collection', 'record'):
            for method in ('get', 'put', 'patch', 'delete'):
                if endpoint_type == 'record':
                    view_name = method
                else:
                    view_name = '_'.join((endpoint_type, method))
                setattr(self, view_name, getattr(mock.sentinel, view_name))


class ViewSetTest(unittest.TestCase):

    def test_arguments_are_merged_on_initialization(self):
        viewset = ViewSet(collection_path=mock.sentinel.collection_path)
        self.assertEquals(viewset.collection_path,
                          mock.sentinel.collection_path)

    def test_default_arguments_are_copied_before_being_returned(self):
        original_arguments = {}
        viewset = ViewSet(
            collection_get_arguments=original_arguments,
            validate_schema_for=()
        )
        arguments = viewset.collection_arguments(mock.sentinel.resource, 'GET')
        self.assertEquals(original_arguments, {})
        self.assertNotEquals(original_arguments, arguments)

    def test_permission_private_is_set_by_default(self):
        viewset = ViewSet()
        args = viewset.collection_arguments(mock.sentinel.resource, 'GET')
        self.assertEquals(args['permission'], 'private')

    def test_schema_is_added_when_method_matches(self):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = mock.MagicMock(mapping=colander.SchemaNode(colander.Int()))
        arguments = viewset.collection_arguments(resource, 'GET')
        schema = arguments['schema']
        self.assertEquals(schema.children[0], resource.mapping)

    def test_schema_is_added_when_uppercase_method_matches(self):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = mock.MagicMock(mapping=colander.SchemaNode(colander.Int()))
        arguments = viewset.collection_arguments(resource, 'get')
        schema = arguments['schema']
        self.assertEquals(schema.children[0], resource.mapping)

    @mock.patch('kinto.core.resource.viewset.colander')
    def test_a_default_schema_is_added_when_method_doesnt_match(self, mocked):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = mock.MagicMock()
        mocked.MappingSchema.return_value = mock.sentinel.default_schema

        arguments = viewset.collection_arguments(resource, 'POST')
        self.assertEquals(arguments['schema'], mock.sentinel.default_schema)
        self.assertNotEqual(arguments['schema'], resource.mapping)

        mocked.MappingSchema.assert_called_with(unknown='preserve')

    def test_class_parameters_are_used_for_collection_arguments(self):
        default_arguments = {
            'cors_headers': mock.sentinel.cors_headers,
        }

        default_get_arguments = {
            'accept': mock.sentinel.accept,
        }

        default_collection_arguments = {
            'cors_origins': mock.sentinel.cors_origins,
        }

        collection_get_arguments = {
            'error_handler': mock.sentinel.error_handler
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_get_arguments=default_get_arguments,
            default_collection_arguments=default_collection_arguments,
            collection_get_arguments=collection_get_arguments
        )

        arguments = viewset.collection_arguments(mock.MagicMock, 'get')
        arguments.pop('schema')
        self.assertDictEqual(
            arguments,
            {
                'accept': mock.sentinel.accept,
                'cors_headers': mock.sentinel.cors_headers,
                'cors_origins': mock.sentinel.cors_origins,
                'error_handler': mock.sentinel.error_handler,
            }
        )

    def test_default_arguments_are_used_for_record_arguments(self):
        default_arguments = {
            'cors_headers': mock.sentinel.cors_headers,
        }

        default_get_arguments = {
            'accept': mock.sentinel.accept,
        }

        default_record_arguments = {
            'cors_origins': mock.sentinel.record_cors_origins,
        }

        record_get_arguments = {
            'error_handler': mock.sentinel.error_handler
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_get_arguments=default_get_arguments,
            default_record_arguments=default_record_arguments,
            record_get_arguments=record_get_arguments
        )

        arguments = viewset.record_arguments(mock.MagicMock, 'get')
        arguments.pop('schema')

        self.assertDictEqual(
            arguments,
            {
                'accept': mock.sentinel.accept,
                'cors_headers': mock.sentinel.cors_headers,
                'cors_origins': mock.sentinel.record_cors_origins,
                'error_handler': mock.sentinel.error_handler,
            }
        )

    def test_class_parameters_overwrite_each_others(self):
        # Some class parameters should overwrite each others.
        # The more specifics should prevail over the more generics.
        # Items annoted with a "<<" are the one that should prevail.
        default_arguments = {
            'cors_origins': mock.sentinel.default_cors_origins,
            'error_handler': mock.sentinel.default_error_handler,
            'cors_headers': mock.sentinel.default_cors_headers,  # <<
        }
        default_record_arguments = {
            'cors_origins': mock.sentinel.default_record_cors_origin,
            'error_handler': mock.sentinel.default_record_error_handler,  # <<
        }

        record_get_arguments = {
            'cors_origins': mock.sentinel.record_get_cors_origin,  # <<
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_record_arguments=default_record_arguments,
            record_get_arguments=record_get_arguments,
        )

        arguments = viewset.record_arguments(mock.MagicMock, 'get')
        arguments.pop('schema')

        self.assertDictEqual(
            arguments,
            {
                'cors_headers': mock.sentinel.default_cors_headers,
                'error_handler': mock.sentinel.default_record_error_handler,
                'cors_origins': mock.sentinel.record_get_cors_origin,
            }
        )

    def test_service_arguments_arent_inherited_by_record_arguments(self):
        service_arguments = {
            'description': 'The little book of calm',
        }

        default_arguments = {
            'cors_headers': mock.sentinel.cors_headers,
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            service_arguments=service_arguments,
            default_record_arguments={},
            record_get_arguments={}
        )

        arguments = viewset.record_arguments(mock.MagicMock, 'get')
        arguments.pop('schema')
        self.assertDictEqual(
            arguments,
            {
                'cors_headers': mock.sentinel.cors_headers,
            }
        )

    def test_get_service_name_returns_the_viewset_name_if_defined(self):
        viewset = ViewSet(name='fakename')
        self.assertEquals(
            viewset.get_service_name('record', mock.MagicMock),
            'fakename-record')

    def test_get_service_name_returns_resource_att_if_not_callable(self):
        viewset = ViewSet()
        resource = mock.MagicMock()
        resource.name = 'fakename'
        self.assertEquals(
            viewset.get_service_name('record', resource),
            'fakename-record')

    def test_get_service_name_doesnt_use_callable_as_a_name(self):
        viewset = ViewSet()
        resource = mock.MagicMock()
        resource.name = lambda x: 'should not be called'
        resource.__name__ = "FakeName"
        self.assertEquals(
            viewset.get_service_name('record', resource),
            'fakename-record')

    def test_get_service_arguments_has_no_factory_by_default(self):
        viewset = ViewSet()
        service_arguments = viewset.get_service_arguments()
        self.assertNotIn('factory', service_arguments)

    def test_is_endpoint_enabled_returns_true_if_unknown(self):
        viewset = ViewSet()
        config = {}
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'get',
                                                 config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_false_if_disabled(self):
        viewset = ViewSet()
        config = {
            'record_fake_get_enabled': False
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'get',
                                                 config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_true_if_enabled(self):
        viewset = ViewSet()
        config = {
            'record_fake_get_enabled': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'get',
                                                 config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_put_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'put',
                                                 config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_post_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'post',
                                                 config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_patch_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'patch',
                                                 config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_false_for_delete_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'delete',
                                                 config)
        self.assertFalse(is_enabled)

    def test_is_endpoint_enabled_returns_true_for_get_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'get',
                                                 config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_true_for_options_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'options',
                                                 config)
        self.assertTrue(is_enabled)

    def test_is_endpoint_enabled_returns_true_for_head_if_readonly(self):
        viewset = ViewSet()
        config = {
            'readonly': True
        }
        is_enabled = viewset.is_endpoint_enabled('record', 'fake', 'head',
                                                 config)
        self.assertTrue(is_enabled)


class ShareableViewSetTest(unittest.TestCase):
    def test_permission_dynamic_is_set_by_default(self):
        viewset = ShareableViewSet()
        args = viewset.collection_arguments(mock.sentinel.resource, 'GET')
        self.assertEquals(args['permission'], 'dynamic')

    def test_get_service_arguments_has_default_factory(self):
        viewset = ShareableViewSet()
        args = viewset.get_service_arguments()
        self.assertEqual(args['factory'], authorization.RouteFactory)


class RegisterTest(unittest.TestCase):

    def setUp(self):
        self.resource = FakeResource
        self.viewset = FakeViewSet()

    @mock.patch('kinto.core.resource.Service')
    def test_register_fails_if_no_storage_backend_is_configured(self, *args):
        venusian_callback = register_resource(
            self.resource, viewset=self.viewset)
        context = mock.MagicMock()
        config = testing.setUp(settings=DEFAULT_SETTINGS)
        context.config.with_package.return_value = config
        try:
            venusian_callback(context, None, None)
        except exceptions.ConfigurationError as e:
            error = e
        self.assertIn('storage backend is missing', str(error))

    @mock.patch('kinto.core.resource.Service')
    def test_viewset_is_updated_if_provided(self, service_class):
        additional_params = {'foo': 'bar'}
        register_resource(self.resource, viewset=self.viewset,
                          **additional_params)
        self.viewset.update.assert_called_with(**additional_params)

    def test_resource_default_viewset_is_used_if_not_provided(self):
        resource = FakeResource
        resource.default_viewset = mock.Mock()
        additional_params = {'foo': 'bar'}
        register_resource(resource, **additional_params)
        resource.default_viewset.assert_called_with(**additional_params)

    @mock.patch('kinto.core.resource.Service')
    def test_collection_views_are_registered_in_cornice(self, service_class):
        venusian_callback = register_resource(
            self.resource, viewset=self.viewset)

        config = mock.MagicMock()
        config.registry.settings = DEFAULT_SETTINGS

        context = mock.MagicMock()
        context.config.with_package.return_value = config
        venusian_callback(context, None, None)

        service_class.assert_any_call('fake-collection', '/fake', depth=1,
                                      **self.viewset.get_service_arguments())
        service_class().add_view.assert_any_call(
            'GET', 'collection_get', klass=self.resource)

    @mock.patch('kinto.core.resource.Service')
    def test_record_views_are_registered_in_cornice(self, service_class):
        venusian_callback = register_resource(
            self.resource, viewset=self.viewset)

        config = mock.MagicMock()
        config.registry.settings = DEFAULT_SETTINGS

        context = mock.MagicMock()
        context.config.with_package.return_value = config
        venusian_callback(context, None, None)

        service_class.assert_any_call('fake-record', '/fake/{id}', depth=1,
                                      **self.viewset.get_service_arguments())
        service_class().add_view.assert_any_call(
            'PUT', 'put', klass=self.resource)

    @mock.patch('kinto.core.resource.Service')
    def test_collection_methods_are_skipped_if_not_enabled(self, service_cls):
        venusian_callback = register_resource(
            self.resource, viewset=self.viewset)

        context = mock.MagicMock()
        context.registry.settings = {
            'record_fake_put_enabled': False
        }
        context.config.with_package.return_value = context
        venusian_callback(context, None, None)

        # Only the collection views should have been added.
        # 3 calls: two registering the service classes,
        # one for the collection_get
        self.assertEquals(len(service_cls.mock_calls), 3)
        service_cls.assert_any_call('fake-collection', '/fake', depth=1,
                                    **self.viewset.get_service_arguments())
        service_cls().add_view.assert_any_call(
            'GET', 'collection_get', klass=self.resource)

    @mock.patch('kinto.core.resource.Service')
    def test_record_methods_are_skipped_if_not_enabled(self, service_class):
        venusian_callback = register_resource(
            self.resource, viewset=self.viewset)

        context = mock.MagicMock()
        context.config.with_package.return_value = context
        context.registry.settings = {
            'collection_fake_get_enabled': False
        }
        venusian_callback(context, None, None)

        # Only the collection views should have been added.
        # 3 calls: two registering the service classes,
        # one for the collection_get
        self.assertEquals(len(service_class.mock_calls), 3)
        service_class.assert_any_call('fake-record', '/fake/{id}', depth=1,
                                      **self.viewset.get_service_arguments())
        service_class().add_view.assert_any_call(
            'PUT', 'put', klass=self.resource)
