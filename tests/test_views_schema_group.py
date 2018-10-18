from kinto.core.testing import unittest

from .support import BaseWebTest


BUCKET_URL = "/buckets/blog"
GROUP_URL = "/buckets/blog/groups/tarnac-nine"


SCHEMA = {
    "title": "Group schema",
    "type": "object",
    "required": ["phone"],
    "properties": {
        "phone": {"type": "string"},
        "members": {"type": "array", "items": {"type": "string"}},
    },
}

VALID_GROUP = {"members": ["oidc:coupat"], "phone": "+33688776655"}


class DeactivatedSchemaTest(BaseWebTest, unittest.TestCase):
    def test_schema_should_be_json_schema(self):
        newschema = {**SCHEMA, "type": "Washmachine"}
        resp = self.app.put_json(
            BUCKET_URL, {"data": {"group:schema": newschema}}, headers=self.headers, status=400
        )
        error_msg = "'Washmachine' is not valid under any of the given schemas"
        self.assertIn(error_msg, resp.json["message"])

    def test_group_are_not_invalid_if_do_not_match_schema(self):
        self.app.put_json(BUCKET_URL, {"data": {"group:schema": SCHEMA}}, headers=self.headers)
        self.app.put_json(GROUP_URL, {"data": {"phone": 42}}, headers=self.headers, status=201)


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
            BUCKET_URL, {"data": {"group:schema": SCHEMA}}, headers=self.headers
        )
        self.collection = resp.json["data"]

    def test_empty_metadata_can_be_validated(self):
        self.app.post_json(BUCKET_URL + "/groups", headers=self.headers, status=400)
        self.app.post_json(BUCKET_URL + "/groups", {"data": {}}, headers=self.headers, status=400)

    def test_groups_are_valid_if_match_schema(self):
        self.app.put_json(GROUP_URL, {"data": VALID_GROUP}, headers=self.headers, status=201)

    def test_groups_are_invalid_if_do_not_match_schema(self):
        self.app.put_json(GROUP_URL, {"data": {"phone": 42}}, headers=self.headers, status=400)


SCHEMA_UNRESOLVABLE = {"properties": {"phone": {"$ref": "#/definitions/phone"}}}


class CollectionUnresolvableTest(BaseWebTestWithSchema, unittest.TestCase):
    def setUp(self):
        super().setUp()
        resp = self.app.put_json(
            BUCKET_URL, {"data": {"group:schema": SCHEMA_UNRESOLVABLE}}, headers=self.headers
        )
        self.collection = resp.json["data"]

    def test_unresolvable_errors_handled(self):
        self.app.put_json(GROUP_URL, {"data": {"phone": 42}}, headers=self.headers, status=400)
