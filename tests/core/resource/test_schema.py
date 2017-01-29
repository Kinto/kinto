import six
import colander
import mock

from kinto.core.testing import unittest
from kinto.core.resource import schema


class TimeStampTest(unittest.TestCase):
    @mock.patch('kinto.core.resource.schema.msec_time')
    def test_default_value_comes_from_timestamper(self, time_mocked):
        time_mocked.return_value = 666
        default = schema.TimeStamp().deserialize(colander.null)
        self.assertEqual(default, 666)


class URLTest(unittest.TestCase):
    def test_supports_full_url(self):
        url = 'https://user:pass@myserver:9999/feeling.html#anchor'
        deserialized = schema.URL().deserialize(url)
        self.assertEqual(deserialized, url)

    def test_raises_invalid_if_no_scheme(self):
        url = 'myserver/feeling.html#anchor'
        self.assertRaises(colander.Invalid,
                          schema.URL().deserialize,
                          url)


class ResourceSchemaTest(unittest.TestCase):

    def test_preserves_unknown_fields_when_specified(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                preserve_unknown = True

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({'foo': 'bar'})
        self.assertIn('foo', deserialized)
        self.assertEquals(deserialized['foo'], 'bar')

    def test_ignore_unknwon_fields_when_specified(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                preserve_unknown = False

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({'foo': 'bar'})
        self.assertNotIn('foo', deserialized)

    def test_accepts_unknown_fields_by_default(self):
        schema_instance = schema.ResourceSchema()
        deserialized = schema_instance.deserialize({'foo': 'bar'})
        self.assertIn('foo', deserialized)

    def test_options_parameters_use_default_value_when_subclassed(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                pass

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({'foo': 'bar'})
        self.assertIn('foo', deserialized)


class PermissionsSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.PermissionsSchema()

    def test_works_with_any_permission_name_by_default(self):
        perms = {'can_cook': ['mat']}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_works_with_empty_mapping(self):
        perms = {}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_works_with_empty_list_of_principals(self):
        perms = {'can_cook': []}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_raises_invalid_if_permission_is_unknown(self):
        self.schema.known_perms = ('can_sleep',)
        perms = {'can_work': ['mat']}
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          perms)

    def test_raises_invalid_if_not_list(self):
        perms = {'can_cook': 3.14}
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          perms)

    def test_raises_invalid_if_not_list_of_strings(self):
        perms = {'can_cook': ['pi', 3.14]}
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          perms)


class HeaderFieldSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.HeaderField(colander.String())

    def test_decode_unicode(self):
        value = six.u('\xe7 is not a c')
        deserialized = self.schema.deserialize(value.encode('utf-8'))
        self.assertEquals(deserialized, value)

    def test_bad_unicode_raises_invalid(self):
        value = b'utf8 \xe9'
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          value)


class QueryFieldSchemaTest(unittest.TestCase):

    def test_deserialize_integer_between_quotes(self):
        self.schema = schema.QueryField(colander.Integer())
        deserialized = self.schema.deserialize("123")
        self.assertEquals(deserialized, 123)


class FieldListSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.FieldList()

    def test_deserialize_as_list(self):
        value = 'foo,-bar,123'
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, ['foo', '-bar', '123'])

    def test_handle_drop(self):
        value = colander.null
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, colander.drop)

    def test_handle_empty(self):
        value = ''
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, [])

    def test_raises_invalid_if_not_string(self):
        value = 123
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          value)


class HeaderQuotedIntegerSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.HeaderQuotedInteger()

    def test_deserialize_as_integer(self):
        value = '"123"'
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, 123)

    def test_deserialize_any(self):
        value = '*'
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, '*')

    def test_unquoted_raises_invalid(self):
        value = '123'
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          value)

    def test_integer_raises_invalid(self):
        value = 123
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          value)

    def test_invalid_quoted_raises_invalid(self):
        value = 'foo'
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          value)

    def test_empty_raises_invalid(self):
        value = '""'
        self.assertRaises(colander.Invalid,
                          self.schema.deserialize,
                          value)


class RequestSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.RequestSchema()

    def test_header_preserve_unkown_fields(self):
        value = {'header': {'foo': 'bar'}}
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, value)

    def test_querystring_preserve_unkown_fields(self):
        value = {'querystring': {'foo': 'bar'}}
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, value)

    def test_drops(self):
        deserialized = self.schema.deserialize({})
        self.assertEquals(deserialized, {})


class GetRequestSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.GetRequestSchema()

    def test_get_deserialize_fields(self):
        value = {'querystring': {'_fields': 'foo,bar'}}
        deserialized = self.schema.deserialize(value)
        expected = {'querystring': {'_fields': ['foo', 'bar']}}
        self.assertEquals(deserialized, expected)


class PatchRequestSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.PatchRequestSchema()

    def test_patch_deserialize_response_behavior(self):
        value = {'header': {'Response-Behavior': 'diff'}}
        deserialized = self.schema.deserialize(value)
        self.assertEquals(deserialized, value)

    def test_patch_validate_response_behavior(self):
        invalid = {'header': {'Response-Behavior': 'impolite'}}
        self.assertRaises(colander.Invalid, self.schema.deserialize, invalid)


class CollectionRequestSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.CollectionRequestSchema()

    def test_collection_deserialize_sort(self):
        value = {'querystring': {'_sort': 'foo,-bar'}}
        deserialized = self.schema.deserialize(value)
        expected = {'querystring': {'_sort': ['foo', '-bar']}}
        self.assertEquals(deserialized, expected)

    def test_collection_validate_limit(self):
        invalid = {'querystring': {'_limit': 'foo'}}
        self.assertRaises(colander.Invalid, self.schema.deserialize, invalid)

    def test_collection_validate_since(self):
        invalid = {'querystring': {'_since': 'bar'}}
        self.assertRaises(colander.Invalid, self.schema.deserialize, invalid)

    def test_collection_validate_to(self):
        invalid = {'querystring': {'_to': 'qux'}}
        self.assertRaises(colander.Invalid, self.schema.deserialize, invalid)

    def test_collection_validate_before(self):
        invalid = {'querystring': {'_before': 'bah'}}
        self.assertRaises(colander.Invalid, self.schema.deserialize, invalid)

    def test_collection_validate_last_modified(self):
        invalid = {'querystring': {'last_modified': 'yesterday'}}
        self.assertRaises(colander.Invalid, self.schema.deserialize, invalid)


class CollectionGetRequestSchemaTest(unittest.TestCase):

    def setUp(self):
        self.schema = schema.CollectionGetRequestSchema()

    def test_deserialize_get_fields(self):
        value = {'querystring': {'_fields': 'foo,bar'}}
        deserialized = self.schema.deserialize(value)
        expected = {'querystring': {'_fields': ['foo', 'bar']}}
        self.assertEquals(deserialized, expected)

    def test_deserialize_collection_fields(self):
        value = {'querystring': {'_sort': 'foo,-bar'}}
        deserialized = self.schema.deserialize(value)
        expected = {'querystring': {'_sort': ['foo', '-bar']}}
        self.assertEquals(deserialized, expected)
