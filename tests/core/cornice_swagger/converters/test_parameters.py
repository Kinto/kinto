import unittest

import colander

from kinto.core.cornice_swagger.converters import convert_parameter, convert_schema
from kinto.core.cornice_swagger.converters.exceptions import NoSuchConverter


class ParameterConversionTest(unittest.TestCase):
    def test_path(self):
        node = colander.SchemaNode(colander.String(), name="foo")
        ret = convert_parameter("path", node)
        self.assertDictEqual(
            ret,
            {
                "in": "path",
                "name": "foo",
                "type": "string",
                "required": True,
            },
        )

    def test_query(self):
        node = colander.SchemaNode(colander.String(), name="bar")
        ret = convert_parameter("querystring", node)
        self.assertDictEqual(
            ret,
            {
                "in": "query",
                "name": "bar",
                "type": "string",
                "required": True,
            },
        )

    def test_query_array(self):
        class MyArray(colander.SequenceSchema):
            values = colander.SchemaNode(colander.String())

        node = MyArray(name="bar")
        ret = convert_parameter("querystring", node)
        self.assertDictEqual(
            ret,
            {
                "in": "query",
                "name": "bar",
                "type": "array",
                "items": {"type": "string"},
                "required": True,
            },
        )

    def test_header(self):
        node = colander.SchemaNode(colander.String(), name="meh")
        ret = convert_parameter("headers", node)
        self.assertDictEqual(
            ret,
            {
                "in": "header",
                "name": "meh",
                "type": "string",
                "required": True,
            },
        )

    def test_body_array(self):
        class MyArray(colander.SequenceSchema):
            values = colander.SchemaNode(colander.String())

        node = MyArray(name="bla")
        ret = convert_parameter("body", node)
        self.assertDictEqual(
            ret,
            {
                "in": "body",
                "name": "bla",
                "required": True,
                "schema": convert_schema(MyArray(title="MyArray")),
            },
        )

    def test_body(self):
        class MyBody(colander.MappingSchema):
            foo = colander.SchemaNode(colander.String())
            bar = colander.SchemaNode(colander.String())

        node = MyBody(name="bla")
        ret = convert_parameter("body", node)
        self.assertDictEqual(
            ret,
            {
                "in": "body",
                "name": "bla",
                "required": True,
                "schema": convert_schema(MyBody(title="MyBody")),
            },
        )

    def test_supports_description(self):
        node = colander.SchemaNode(colander.String(), name="bar", description="tyred")
        ret = convert_parameter("querystring", node)
        self.assertDictEqual(
            ret,
            {
                "in": "query",
                "name": "bar",
                "type": "string",
                "required": True,
                "description": "tyred",
            },
        )

    def test_raise_no_such_converter_on_invalid_location(self):
        node = colander.SchemaNode(colander.String(), name="foo")
        self.assertRaises(NoSuchConverter, convert_parameter, "aaa", node)
