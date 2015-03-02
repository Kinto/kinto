import colander
import mock

from cliquet.tests.support import unittest
from cliquet import schema


class TimeStampTest(unittest.TestCase):
    @mock.patch('cliquet.schema.msec_time')
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

    def test_ignore_unknwon_fields_by_default(self):
        schema_instance = schema.ResourceSchema()
        deserialized = schema_instance.deserialize({'foo': 'bar'})
        self.assertNotIn('foo', deserialized)

    def test_options_parameters_use_default_value_when_subclassed(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                pass

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({'foo': 'bar'})
        self.assertNotIn('foo', deserialized)
