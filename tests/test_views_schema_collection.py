from kinto.core.testing import unittest

from .support import BaseWebTest


BUCKET_URL = "/buckets/blog"
COLLECTION_URL = "/buckets/blog/collections/articles"


SCHEMA = {
    "title": "Collection schema",
    "type": "object",
    "required": ["displayFields"],
    "properties": {
        "uiSchema": {"type": "object"},
        "displayFields": {"type": "array", "items": {"type": "string"}},
    },
}

VALID_COLLECTION = {"uiSchema": {"schema": {"ui:widget": "hidden"}}, "displayFields": ["name"]}


class DeactivatedSchemaTest(BaseWebTest, unittest.TestCase):
    def test_schema_should_be_json_schema(self):
        newschema = {**SCHEMA, "type": "Washmachine"}
        resp = self.app.put_json(
            BUCKET_URL,
            {"data": {"collection:schema": newschema}},
            headers=self.headers,
            status=400,
        )
        error_msg = "'Washmachine' is not valid under any of the given schemas"
        self.assertIn(error_msg, resp.json["message"])

    def test_records_are_not_invalid_if_do_not_match_schema(self):
        self.app.put_json(
            BUCKET_URL, {"data": {"collection:schema": SCHEMA}}, headers=self.headers
        )
        self.app.put_json(
            COLLECTION_URL, {"data": {"displayFields": 42}}, headers=self.headers, status=201
        )


class BaseWebTestWithSchema(BaseWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["experimental_collection_schema_validation"] = "True"
        return settings


class CollectionValidationTest(BaseWebTestWithSchema, unittest.TestCase):
    def setUp(self):
        super().setUp()
        resp = self.app.put_json(
            BUCKET_URL, {"data": {"collection:schema": SCHEMA}}, headers=self.headers
        )
        self.collection = resp.json["data"]

    def test_empty_metadata_can_be_validated(self):
        self.app.post_json(BUCKET_URL + "/collections", headers=self.headers, status=400)
        self.app.post_json(
            BUCKET_URL + "/collections", {"data": {}}, headers=self.headers, status=400
        )

    def test_collections_are_valid_if_match_schema(self):
        self.app.put_json(
            COLLECTION_URL, {"data": VALID_COLLECTION}, headers=self.headers, status=201
        )

    def test_collections_are_invalid_if_do_not_match_schema(self):
        self.app.put_json(
            COLLECTION_URL, {"data": {"displayFields": 42}}, headers=self.headers, status=400
        )


SCHEMA_UNRESOLVABLE = {"properties": {"displayFields": {"$ref": "#/definitions/displayFields"}}}


class CollectionUnresolvableTest(BaseWebTestWithSchema, unittest.TestCase):
    def setUp(self):
        super().setUp()
        resp = self.app.put_json(
            BUCKET_URL, {"data": {"collection:schema": SCHEMA_UNRESOLVABLE}}, headers=self.headers
        )
        self.collection = resp.json["data"]

    def test_unresolvable_errors_handled(self):
        self.app.put_json(
            COLLECTION_URL, {"data": {"displayFields": 42}}, headers=self.headers, status=400
        )
