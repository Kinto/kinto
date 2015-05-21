from mock import sentinel, MagicMock, patch

from cliquet.resource import ViewSet, register

from .support import unittest

class FakeViewSet(object):
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
        patched.from_colander.return_value = sentinel.schema
        arguments = viewset.collection_arguments(resource, 'GET')
        patched.from_colander.assert_called_with(resource.mapping,
                                                 bind_request=False)
        self.assertEquals(arguments['schema'], sentinel.schema)

    @patch('cliquet.resource.CorniceSchema')
    def test_schema_is_added_when_case_doesnt_match(self, patched):
        viewset = ViewSet(
            validate_schema_for=('GET', )
        )
        resource = MagicMock()
        patched.from_colander.return_value = sentinel.schema
        arguments = viewset.collection_arguments(resource, 'get')
        patched.from_colander.assert_called_with(resource.mapping,
                                                 bind_request=False)
        self.assertEquals(arguments['schema'], sentinel.schema)

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
            'description': 'This is one description of {resource_name}',
        }
        default_collection_arguments = {
            'cors_origins': ('example.org',),
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
                'description': 'This is one description of {resource_name}',
                'cors_origins': ('example.org',),
                'error_handler': sentinel.error_handler
            }
        )

    def test_class_parameters_are_used_for_record_arguments(self):
        default_arguments = {
            'description': 'This is one description of {resource_name}',
        }
        default_record_arguments = {
            'cors_origins': ('example.org',),
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
                'description': 'This is one description of {resource_name}',
                'cors_origins': ('example.org',),
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
            'description': sentinel.default_description,  # <<
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
                'description': sentinel.default_description,
                'error_handler': sentinel.default_record_error_handler,
                'cors_origins': sentinel.record_get_cors_origin,
            }
        )


class RegisterTest(unittest.TestCase):

    def setUp(self):
        self.resource = FakeResource()
        self.viewset = FakeViewSet()

    @patch('cliquet.resource.Service')
    def test_viewset_is_updated_if_provided(self, service_class):
        additional_params = {'foo': 'bar'}
        register(self.resource, viewset=self.viewset, **additional_params)
        self.viewset.update.assert_called_with(**additional_params)

    @patch('cliquet.resource.Service')
    def test_collection_views_are_registered_in_cornice(self, service_class):
        register(self.resource, viewset=self.viewset)

        service_class.assert_any_call(self.resource.name, '/fake')
        service_class().add_view.assert_any_call(
            'GET', sentinel.collection_get)

    @patch('cliquet.resource.Service')
    def test_record_views_are_registered_in_cornice(self, service_class):
        register(self.resource, viewset=self.viewset)

        service_class.assert_any_call(self.resource.name, '/fake/{id}')
        service_class().add_view.assert_any_call(
            'PUT', sentinel.record_put)


    @patch('cliquet.resource.Service')
    def test_record_methods_are_skipped_if_not_enabled(self, service_class):
        register(self.resource, viewset=self.viewset, settings={
            'cliquet.record_fake_put_enabled': False
        })

        # Only the collection views should have been added.
        # 3 calls: two registering the service classes,
        # one for the collection_get
        self.assertEquals(len(service_class.mock_calls), 3)
        service_class.assert_any_call(self.resource.name, '/fake')
        service_class().add_view.assert_any_call(
            'GET', sentinel.collection_get)


    @patch('cliquet.resource.Service')
    def test_record_methods_are_skipped_if_not_enabled(self, service_class):
        register(self.resource, viewset=self.viewset, settings={
            'cliquet.collection_fake_get_enabled': False
        })

        # Only the collection views should have been added.
        # 3 calls: two registering the service classes,
        # one for the collection_get
        self.assertEquals(len(service_class.mock_calls), 3)
        service_class.assert_any_call(self.resource.name, '/fake/{id}')
        service_class().add_view.assert_any_call(
            'PUT', sentinel.record_put)

