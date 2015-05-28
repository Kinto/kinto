from mock import sentinel, MagicMock, patch

from cliquet.resource import ViewSet, register_resource

from .support import unittest

class FakeViewSet(ViewSet):
    """Fake viewset class used for tests."""
    collection_path = "/{resource_name}"
    record_path = "/{resource_name}/{{id}}"

    collection_methods = ('GET',)
    record_methods = ('PUT',)

    def __init__(self):
        self.collection_arguments = self.arguments
        self.record_arguments = self.arguments
        self.update = MagicMock()

    def arguments(self, resource, method):
        # By default, returns an empty dict of arguments.
        return {}


class FakeResource(object):
    """Fake resource class used for tests"""
    name = "fake"

    def __init__(self):
        # Create fake views which are in fact mock sentinels.
        # {type}_{method} will map to the sentinel with the same name.
        for typ_ in ('collection', 'record'):
            for method in ('get', 'put', 'patch', 'delete'):
                if typ_ == 'record':
                    view_name = method
                else:
                    view_name = '_'.join((typ_, method))
                setattr(self, view_name, getattr(sentinel, view_name))


class ViewSetTest(unittest.TestCase):

    def test_arguments_are_merged_on_initialization(self):
        viewset = ViewSet(collection_path=sentinel.collection_path)
        self.assertEquals(viewset.collection_path,
                          sentinel.collection_path)

    def test_default_arguments_are_copied_before_being_returned(self):
        original_arguments = {}
        viewset = ViewSet(
            collection_get_arguments=original_arguments,
            validate_schema_for=()
        )
        arguments = viewset.collection_arguments(sentinel.resource, 'GET')
        self.assertEquals(original_arguments, {})

    @patch('cliquet.resource.CorniceSchema')
    def test_schema_is_added_when_method_matches(self, patched):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = MagicMock()
        arguments = viewset.collection_arguments(resource, 'GET')
        self.assertEquals(arguments['schema'], resource.mapping)

    @patch('cliquet.resource.CorniceSchema')
    def test_schema_is_added_when_method_is_uppercase(self, patched):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = MagicMock()
        arguments = viewset.collection_arguments(resource, 'get')
        self.assertEquals(arguments['schema'], resource.mapping)

    @patch('cliquet.resource.CorniceSchema')
    def test_schema_is_not_added_when_method_does_not_match(self, patched):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = MagicMock()
        arguments = viewset.collection_arguments(resource, 'POST')
        patched.from_colander.assert_not_called()
        self.assertNotIn('schema', arguments)

    def test_class_parameters_are_used_for_collection_arguments(self):
        default_arguments = {
            'cors_headers': sentinel.cors_headers,
        }
        default_collection_arguments = {
            'cors_origins': sentinel.cors_origins,
        }

        collection_get_arguments = {
            'error_handler': sentinel.error_handler
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_collection_arguments=default_collection_arguments,
            collection_get_arguments=collection_get_arguments
        )

        arguments = viewset.collection_arguments(MagicMock, 'get')
        self.assertDictEqual(
            arguments,
            {
                'cors_headers': sentinel.cors_headers,
                'cors_origins': sentinel.cors_origins,
                'error_handler': sentinel.error_handler
            }
        )

    def test_default_arguments_are_used_for_record_arguments(self):
        default_arguments = {
            'cors_headers': sentinel.cors_headers,
        }
        default_record_arguments = {
            'cors_origins': sentinel.record_cors_origins,
        }

        record_get_arguments = {
            'error_handler': sentinel.error_handler
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_record_arguments=default_record_arguments,
            record_get_arguments=record_get_arguments
        )

        arguments = viewset.record_arguments(MagicMock, 'get')
        self.assertDictEqual(
            arguments,
            {
                'cors_headers': sentinel.cors_headers,
                'cors_origins': sentinel.record_cors_origins,
                'error_handler': sentinel.error_handler
            }
        )

    def test_class_parameters_overwrite_each_others(self):
        # Some class parameters should overwrite each others.
        # The more specifics should prevail over the more generics.
        # Items annoted with a "<<" are the one that should prevail.
        default_arguments = {
            'cors_origins': sentinel.default_cors_origins,
            'error_handler': sentinel.default_error_handler,
            'cors_headers': sentinel.default_cors_headers,  # <<
        }
        default_record_arguments = {
            'cors_origins': sentinel.default_record_cors_origin,
            'error_handler': sentinel.default_record_error_handler,  # <<
        }

        record_get_arguments = {
            'cors_origins': sentinel.record_get_cors_origin,  # <<
        }

        viewset = ViewSet(
            default_arguments=default_arguments,
            default_record_arguments=default_record_arguments,
            record_get_arguments=record_get_arguments,
        )

        arguments = viewset.record_arguments(MagicMock, 'get')
        self.assertDictEqual(
            arguments,
            {
                'cors_headers': sentinel.default_cors_headers,
                'error_handler': sentinel.default_record_error_handler,
                'cors_origins': sentinel.record_get_cors_origin,
            }
        )

    def test_service_arguments_arent_inherited_by_record_arguments(self):
        service_arguments = {
            'description': 'The little book of calm',
        }

        default_arguments = {
            'cors_headers': sentinel.cors_headers,
        }


        viewset = ViewSet(
            default_arguments=default_arguments,
            service_arguments=service_arguments,
            default_record_arguments={},
            record_get_arguments={}
        )

        arguments = viewset.record_arguments(MagicMock, 'get')
        self.assertDictEqual(
            arguments,
            {
                'cors_headers': sentinel.cors_headers,
            }
        )

    def test_get_service_name_returns_the_viewset_name_if_defined(self):
        viewset = ViewSet(name='fakename')
        self.assertEquals(
            viewset.get_service_name('record', MagicMock),
            'fakename-record')

    def test_get_service_name_returns_resource_att_if_not_callable(self):
        viewset = ViewSet()
        resource = MagicMock()
        resource.name = 'fakename'
        self.assertEquals(
            viewset.get_service_name('record', resource),
            'fakename-record')

    def test_get_service_name_doesnt_use_callable_as_a_name(self):
        viewset = ViewSet()
        resource = MagicMock()
        resource.name = lambda x: 'should not be called'
        resource.__name__ = "FakeName"
        self.assertEquals(
            viewset.get_service_name('record', resource),
            'fakename-record')


class RegisterTest(unittest.TestCase):

    def setUp(self):
        self.resource = FakeResource
        self.viewset = FakeViewSet()

    @patch('cliquet.resource.Service')
    def test_viewset_is_updated_if_provided(self, service_class):
        additional_params = {'foo': 'bar'}
        register_resource(self.resource, viewset=self.viewset, **additional_params)
        self.viewset.update.assert_called_with(**additional_params)

    @patch('cliquet.resource.Service')
    def test_collection_views_are_registered_in_cornice(self, service_class):
        register_resource(self.resource, viewset=self.viewset)

        service_class.assert_any_call('fake-collection', '/fake', depth=1)
        service_class().add_view.assert_any_call(
            'GET', 'collection_get', klass=self.resource)

    @patch('cliquet.resource.Service')
    def test_record_views_are_registered_in_cornice(self, service_class):
        register_resource(self.resource, viewset=self.viewset)

        service_class.assert_any_call('fake-record', '/fake/{id}', depth=1)
        service_class().add_view.assert_any_call(
            'PUT', 'put', klass=self.resource)


    @patch('cliquet.resource.Service')
    def test_record_methods_are_skipped_if_not_enabled(self, service_class):
        register_resource(self.resource, viewset=self.viewset, settings={
            'cliquet.record_fake_put_enabled': False
        })

        # Only the collection views should have been added.
        # 3 calls: two registering the service classes,
        # one for the collection_get
        self.assertEquals(len(service_class.mock_calls), 3)
        service_class.assert_any_call('fake-collection', '/fake', depth=1)
        service_class().add_view.assert_any_call(
            'GET', 'collection_get', klass=self.resource)


    @patch('cliquet.resource.Service')
    def test_record_methods_are_skipped_if_not_enabled(self, service_class):
        register_resource(self.resource, viewset=self.viewset, settings={
            'cliquet.collection_fake_get_enabled': False
        })

        # Only the collection views should have been added.
        # 3 calls: two registering the service classes,
        # one for the collection_get
        self.assertEquals(len(service_class.mock_calls), 3)
        service_class.assert_any_call('fake-record', '/fake/{id}', depth=1)
        service_class().add_view.assert_any_call(
            'PUT', 'put', klass=self.resource)

