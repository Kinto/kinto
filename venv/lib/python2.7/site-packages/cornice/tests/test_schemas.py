# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cornice.errors import Errors
from cornice.tests.support import TestCase
from cornice.schemas import (
    CorniceSchema, validate_colander_schema, SchemaError
)
from cornice.util import extract_json_data
import json

try:
    from colander import (
        deferred,
        Mapping,
        MappingSchema,
        Sequence,
        SequenceSchema,
        SchemaNode,
        String,
        Int,
        OneOf,
        drop
    )
    COLANDER = True
except ImportError:
    COLANDER = False

if COLANDER:

    @deferred
    def deferred_validator(node, kw):
        """
        This is a deferred validator that changes its own behavior based on
        request object being passed, thus allowing for validation of fields
        depending on other field values.

        This example shows how to validate a body field based on a dummy
        header value, using OneOf validator with different choices
        """
        request = kw['request']
        if request['x-foo'] == 'version_a':
            return OneOf(['a', 'b'])
        else:
            return OneOf(['c', 'd'])

    class TestingSchema(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")

    class WrongSchema(SequenceSchema):
        items = TestingSchema()

    class InheritedSchema(TestingSchema):
        foo = SchemaNode(Int(), missing=1)

    class ToBoundSchema(TestingSchema):
        foo = SchemaNode(Int(), missing=1)
        bazinga = SchemaNode(String(), type='str', location="body",
                             validator=deferred_validator)

    class DropSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', missing=drop)
        bar = SchemaNode(String(), type='str')

    class StrictMappingSchema(MappingSchema):
        @staticmethod
        def schema_type():
            return Mapping(unknown='raise')

    class StrictSchema(StrictMappingSchema):
        foo = SchemaNode(String(), type='str', location="body", missing=drop)
        bar = SchemaNode(String(), type='str', location="body")

    class NestedSchema(MappingSchema):
        egg = StrictSchema(location='querystring')
        ham = StrictSchema(location='body')

    class DefaultSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', location="querystring",
                         missing=drop, default='foo')
        bar = SchemaNode(String(), type='str', location="querystring",
                         default='bar')

    class DefaultValueSchema(MappingSchema):
        foo = SchemaNode(Int(), type="int")
        bar = SchemaNode(Int(), type="int", default=10)

    class QsSchema(MappingSchema):
        foo = SchemaNode(String(), type='str', location="querystring",
                         missing=drop)

    class StrictQsSchema(StrictMappingSchema):
        foo = SchemaNode(String(), type='str', location="querystring",
                         missing=drop)

    imperative_schema = SchemaNode(Mapping())
    imperative_schema.add(SchemaNode(String(), name='foo', type='str'))
    imperative_schema.add(SchemaNode(String(), name='bar', type='str',
                          location="body"))
    imperative_schema.add(SchemaNode(String(), name='baz', type='str',
                          location="querystring"))

    class TestingSchemaWithHeader(MappingSchema):
        foo = SchemaNode(String(), type='str')
        bar = SchemaNode(String(), type='str', location="body")
        baz = SchemaNode(String(), type='str', location="querystring")
        qux = SchemaNode(String(), type='str', location="header")

    class PreserveUnkownSchema(MappingSchema):
        bar = SchemaNode(String(), type='str')

        @staticmethod
        def schema_type():
            return Mapping(unknown='preserve')

    def get_mock_request(body, get=None):
        # Construct a mock request with the given request body
        class MockRegistry(object):
            def __init__(self):
                self.cornice_deserializers = {
                    'application/json': extract_json_data
                }

        class MockRequest(object):
            def __init__(self, body, get):
                self.headers = {}
                self.matchdict = {}
                self.body = body
                self.GET = get or {}
                self.POST = {}
                self.validated = {}
                self.registry = MockRegistry()
                self.content_type = 'application/json'

        dummy_request = MockRequest(body, get)
        setattr(dummy_request, 'errors', Errors(dummy_request))
        return dummy_request

    class TestSchemas(TestCase):

        def test_colander_integration(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(TestingSchema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)

        def test_colander_integration_with_header(self):
            schema = CorniceSchema.from_colander(TestingSchemaWithHeader)
            all_fields = schema.get_attributes()
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")
            header_fields = schema.get_attributes(location="header")

            self.assertEqual(len(all_fields), 4)
            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)
            self.assertEqual(len(header_fields), 1)

        def test_colander_inheritance(self):
            """
            support inheritance of colander.Schema
            introduced in colander 0.9.9

            attributes of base-classes with the same name than
            subclass-attributes get overwritten.
            """
            base_schema = CorniceSchema.from_colander(TestingSchema)
            inherited_schema = CorniceSchema.from_colander(InheritedSchema)

            self.assertEqual(len(base_schema.get_attributes()),
                             len(inherited_schema.get_attributes()))

            def foo_filter(obj):
                return obj.name == "foo"

            base_foo = list(filter(foo_filter,
                                   base_schema.get_attributes()))[0]
            inherited_foo = list(filter(foo_filter,
                                        inherited_schema.get_attributes()))[0]
            self.assertTrue(base_foo.required)
            self.assertFalse(inherited_foo.required)

        def test_colander_bound_schemas(self):
            dummy_request = {'x-foo': 'version_a'}
            a_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = a_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a', 'b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            b_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = b_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c', 'd'])

        def test_colander_bound_schema_rebinds_to_new_request(self):
            dummy_request = {'x-foo': 'version_a'}
            the_schema = CorniceSchema.from_colander(ToBoundSchema)
            field = the_schema.get_attributes(request=dummy_request)[3]
            self.assertEqual(field.validator.choices, ['a', 'b'])

            other_dummy_request = {'x-foo': 'bazinga!'}
            field = the_schema.get_attributes(request=other_dummy_request)[3]
            self.assertEqual(field.validator.choices, ['c', 'd'])

        def test_colander_request_is_bound_by_default(self):
            the_schema = CorniceSchema.from_colander(ToBoundSchema)
            dummy_request = {'x-foo': 'version_a'}
            field = the_schema.get_attributes(request=dummy_request)[3]
            # Deferred are resolved
            self.assertNotEqual(type(field.validator), deferred)

        def test_colander_request_is_not_bound_if_disabled(self):
            the_schema = CorniceSchema.from_colander(ToBoundSchema,
                                                     bind_request=False)
            dummy_request = {'x-foo': 'version_a'}
            field = the_schema.get_attributes(request=dummy_request)[3]
            # Deferred are not resolved
            self.assertEqual(type(field.validator), deferred)

        def test_imperative_colander_schema(self):
            # not specifying body should act the same way as specifying it
            schema = CorniceSchema.from_colander(imperative_schema)
            body_fields = schema.get_attributes(location="body")
            qs_fields = schema.get_attributes(location="querystring")

            self.assertEqual(len(body_fields), 2)
            self.assertEqual(len(qs_fields), 1)

            dummy_request = get_mock_request('{"bar": "some data"}')
            validate_colander_schema(schema, dummy_request)

        def test_colander_schema_using_drop(self):
            """
            remove fields from validated data if they deserialize to colander's
            `drop` object.
            """
            schema = CorniceSchema.from_colander(DropSchema)

            dummy_request = get_mock_request('{"bar": "required_data"}')
            validate_colander_schema(schema, dummy_request)

            self.assertNotIn('foo', dummy_request.validated)
            self.assertIn('bar', dummy_request.validated)
            self.assertEqual(len(dummy_request.errors), 0)

        def test_colander_strict_schema(self):
            schema = CorniceSchema.from_colander(StrictSchema)

            dummy_request = get_mock_request(
                '''
                {"bar": "required_data", "foo": "optional_data",
                "other": "not_wanted_data"}
                ''')
            validate_colander_schema(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0], {'description': 'other is not allowed',
                                         'location': 'body',
                                         'name': 'other'})
            self.assertIn('foo', dummy_request.validated)
            self.assertIn('bar', dummy_request.validated)

        def test_colander_schema_using_dotted_names(self):
            """
            Schema could be passed as string in view
            """
            schema = CorniceSchema.from_colander(
                'cornice.tests.schema.AccountSchema')

            dummy_request = get_mock_request('{"nickname": "john"}')
            validate_colander_schema(schema, dummy_request)

            self.assertIn('nickname', dummy_request.validated)
            self.assertNotIn('city', dummy_request.validated)

        def test_colander_nested_schema(self):
            schema = CorniceSchema.from_colander(NestedSchema)

            dummy_request = get_mock_request('{"ham": {"bar": "POST"}}',
                                             {'egg.bar': 'GET'})
            validate_colander_schema(schema, dummy_request)

            qs_fields = schema.get_attributes(location="querystring")

            errors = dummy_request.errors
            self.assertEqual(len(errors), 0, errors)
            self.assertEqual(len(qs_fields), 1)

            expected = {'egg': {'bar': 'GET'},
                        'ham': {'bar': 'POST'},
                        }

            self.assertEqual(expected, dummy_request.validated)

        def test_colander_schema_using_defaults(self):
            """
            Schema could contains default values
            """
            schema = CorniceSchema.from_colander(DefaultSchema)

            dummy_request = get_mock_request('', {'bar': 'test'})
            validate_colander_schema(schema, dummy_request)

            qs_fields = schema.get_attributes(location="querystring")

            errors = dummy_request.errors
            self.assertEqual(len(errors), 0)
            self.assertEqual(len(qs_fields), 2)

            expected = {'foo': 'foo', 'bar': 'test'}

            self.assertEqual(expected, dummy_request.validated)

            dummy_request = get_mock_request('', {'bar': 'test',
                                                  'foo': 'test'})
            validate_colander_schema(schema, dummy_request)

            qs_fields = schema.get_attributes(location="querystring")

            errors = dummy_request.errors
            self.assertEqual(len(errors), 0)
            self.assertEqual(len(qs_fields), 2)

            expected = {'foo': 'test', 'bar': 'test'}

            self.assertEqual(expected, dummy_request.validated)

        def test_colander_schema_default_value(self):
            # apply default value to field if the input for them is
            # missing
            schema = CorniceSchema.from_colander(DefaultValueSchema)
            dummy_request = get_mock_request('{"foo": 5}')
            validate_colander_schema(schema, dummy_request)

            self.assertIn('bar', dummy_request.validated)
            self.assertEqual(len(dummy_request.errors), 0)
            self.assertEqual(dummy_request.validated['foo'], 5)
            # default value should be available
            self.assertEqual(dummy_request.validated['bar'], 10)

        def test_only_mapping_is_accepted(self):
            schema = CorniceSchema.from_colander(WrongSchema)
            dummy_request = get_mock_request('', {'foo': 'test',
                                                  'bar': 'test'})
            self.assertRaises(SchemaError,
                              validate_colander_schema, schema, dummy_request)

            # We shouldn't accept a MappingSchema if the `typ` has
            #  been set to something else:
            schema = CorniceSchema.from_colander(
                MappingSchema(
                    Sequence,
                    SchemaNode(String(), name='foo'),
                    SchemaNode(String(), name='bar'),
                    SchemaNode(String(), name='baz')
                )
            )
            self.assertRaises(SchemaError,
                              validate_colander_schema, schema, dummy_request)

        def test_extra_params_qs(self):
            schema = CorniceSchema.from_colander(QsSchema)
            dummy_request = get_mock_request('', {'foo': 'test',
                                                  'bar': 'test'})
            validate_colander_schema(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 0)

            expected = {'foo': 'test'}
            self.assertEqual(expected, dummy_request.validated)

        def test_extra_params_qs_strict(self):
            schema = CorniceSchema.from_colander(StrictQsSchema)
            dummy_request = get_mock_request('', {'foo': 'test',
                                                  'bar': 'test'})
            validate_colander_schema(schema, dummy_request)

            errors = dummy_request.errors
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0], {'description': 'bar is not allowed',
                                         'location': 'querystring',
                                         'name': 'bar'})

            expected = {'foo': 'test'}
            self.assertEqual(expected, dummy_request.validated)

        def test_validate_colander_schema_can_preserve_unknown_fields(self):
            schema = CorniceSchema.from_colander(PreserveUnkownSchema)

            data = json.dumps({"bar": "required_data", "optional": "true"})
            dummy_request = get_mock_request(data)
            validate_colander_schema(schema, dummy_request)

            self.assertDictEqual(dummy_request.validated, {
                "bar": "required_data",
                "optional": "true"
            })
            self.assertEqual(len(dummy_request.errors), 0)
