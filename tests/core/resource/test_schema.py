import colander

from kinto.core.testing import unittest
from kinto.core.resource import schema


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
