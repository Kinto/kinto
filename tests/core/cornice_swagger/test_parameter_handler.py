import unittest

import colander

from kinto.core.cornice_swagger.converters import convert_schema
from kinto.core.cornice_swagger.swagger import DefinitionHandler, ParameterHandler

from .support import (
    AnotherDeclarativeSchema,
    BodySchema,
    DeclarativeSchema,
    HeaderSchema,
    PathSchema,
    QuerySchema,
)


class SchemaParamConversionTest(unittest.TestCase):
    def setUp(self):
        self.handler = ParameterHandler()

    def test_sanity(self):
        node = colander.MappingSchema()
        params = self.handler.from_schema(node)
        self.assertEqual(params, [])

    def test_covert_body_with_request_validator_schema(self):
        class RequestSchema(colander.MappingSchema):
            body = BodySchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)
        self.assertEqual(len(params), 1)

        expected = {
            "name": "BodySchema",
            "in": "body",
            "required": True,
            "schema": convert_schema(BodySchema(title="BodySchema")),
        }

        self.assertDictEqual(params[0], expected)

    def test_covert_query_with_request_validator_schema(self):
        class RequestSchema(colander.MappingSchema):
            querystring = QuerySchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)
        self.assertEqual(len(params), 1)

        expected = {
            "name": "foo",
            "in": "query",
            "type": "string",
            "required": False,
            "minLength": 3,
        }
        self.assertDictEqual(params[0], expected)

    def test_covert_headers_with_request_validator_schema(self):
        class RequestSchema(colander.MappingSchema):
            headers = HeaderSchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)
        self.assertEqual(len(params), 1)

        expected = {
            "name": "bar",
            "in": "header",
            "type": "string",
            "required": False,
        }
        self.assertDictEqual(params[0], expected)

    def test_covert_path_with_request_validator_schema(self):
        class RequestSchema(colander.MappingSchema):
            path = PathSchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)
        self.assertEqual(len(params), 1)

        expected = {
            "name": "meh",
            "in": "path",
            "type": "string",
            "required": True,
            "default": "default",
        }
        self.assertDictEqual(params[0], expected)

    def test_convert_multiple_with_request_validator_schema(self):
        class RequestSchema(colander.MappingSchema):
            body = BodySchema()
            path = PathSchema()
            querystring = QuerySchema()
            headers = HeaderSchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)

        names = [param["name"] for param in params]
        expected = ["BodySchema", "foo", "bar", "meh"]
        self.assertEqual(sorted(names), sorted(expected))

    def test_convert_descriptions(self):
        class RequestSchema(colander.MappingSchema):
            body = BodySchema(description="my body")

        node = RequestSchema()
        params = self.handler.from_schema(node)

        expected = {
            "name": "BodySchema",
            "in": "body",
            "required": True,
            "description": "my body",
            "schema": convert_schema(BodySchema(title="BodySchema", description="my body")),
        }

        self.assertDictEqual(params[0], expected)

    def test_declarative_schema_handling(self):
        handler = ParameterHandler(DefinitionHandler(ref=-1))
        params = handler.from_schema(DeclarativeSchema())
        another_params = handler.from_schema(AnotherDeclarativeSchema())

        self.assertNotEqual(params[0]["schema"], another_params[0]["schema"])

    def test_cornice_location_synonyms(self):
        class RequestSchema(colander.MappingSchema):
            header = HeaderSchema()
            GET = QuerySchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)

        names = [param["name"] for param in params]
        expected = ["foo", "bar"]
        self.assertEqual(sorted(names), sorted(expected))


class PathParamConversionTest(unittest.TestCase):
    def setUp(self):
        self.handler = ParameterHandler()

    def test_from_path(self):
        params = self.handler.from_path("/my/{param}/path/{id}")
        names = [param["name"] for param in params]
        expected = ["param", "id"]
        self.assertEqual(sorted(names), sorted(expected))
        for param in params:
            self.assertEqual(param["in"], "path")

    def test_handles_path_regex(self):
        params = self.handler.from_path("/my/{param:\\d+}/path/{id:[a-z]{8,42}}")
        named_params = {param["name"]: param for param in params}
        expected = ["param", "id"]
        self.assertEqual(sorted(named_params), sorted(expected))
        self.assertEqual(named_params["param"]["pattern"], "\\d+")
        self.assertEqual(named_params["id"]["pattern"], "[a-z]{8,42}")


class RefParamTest(unittest.TestCase):
    def setUp(self):
        self.handler = ParameterHandler(ref=1)
        self.handler.parameters = {}

    def test_ref_from_path(self):
        params = self.handler.from_path("/path/{id}")
        expected = {
            "name": "id",
            "in": "path",
            "type": "string",
            "required": True,
        }

        self.assertEqual(params, [{"$ref": "#/parameters/id"}])
        self.assertDictEqual(self.handler.parameter_registry, dict(id=expected))

    def test_ref_from_declarative_validator_schema(self):
        params = self.handler.from_schema(DeclarativeSchema())
        self.assertEqual([{"$ref": "#/parameters/DeclarativeSchemaBody"}], params)

    def test_ref_from_request_validator_schema(self):
        class RequestSchema(colander.MappingSchema):
            querystring = QuerySchema()

        node = RequestSchema()
        params = self.handler.from_schema(node)

        expected = {
            "name": "foo",
            "in": "query",
            "type": "string",
            "required": False,
            "minLength": 3,
        }

        self.assertEqual(params, [{"$ref": "#/parameters/foo"}])
        self.assertDictEqual(self.handler.parameter_registry, dict(foo=expected))
