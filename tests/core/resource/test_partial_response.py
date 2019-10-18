from pyramid import httpexceptions

from kinto.core.resource import Resource

from . import BaseTest


class PartialResponseBase(BaseTest):
    def setUp(self):
        super().setUp()
        self.resource._get_known_fields = lambda: ["field", "other", "orig"]
        self.obj = self.model.create_object(
            {
                "field": "value",
                "other": "val",
                "orig": {
                    "foo": "food",
                    "bar": "baz",
                    "nested": {"size": 12546, "hash": "0x1254", "mime": "image/png"},
                },
            }
        )
        self.resource.object_id = self.obj["id"]
        self.resource.request = self.get_request()
        self.resource.request.validated = self.validated
        self.validated["querystring"] = {}


class PartialFieldsTest(PartialResponseBase):
    def test_fields_parameter_do_projection_on_get(self):
        self.validated["querystring"]["_fields"] = ["field"]
        obj = self.resource.get()
        self.assertIn("field", obj["data"])
        self.assertNotIn("other", obj["data"])

    def test_fields_parameter_do_projection_on_get_all(self):
        self.validated["querystring"]["_fields"] = ["field"]
        obj = self.resource.plural_get()["data"][0]
        self.assertIn("field", obj)
        self.assertNotIn("other", obj)

    def test_fail_if_fields_parameter_is_invalid(self):
        self.validated["querystring"]["_fields"] = "invalid_field"
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.get)
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)

    def test_can_have_multiple_fields(self):
        self.validated["querystring"]["_fields"] = ["field", "other"]
        obj = self.resource.get()
        self.assertIn("field", obj["data"])
        self.assertIn("other", obj["data"])

    def test_id_and_last_modified_are_not_filtered(self):
        self.validated["querystring"]["_fields"] = ["field"]
        obj = self.resource.get()
        self.assertIn("id", obj["data"])
        self.assertIn("last_modified", obj["data"])

    def test_nested_parameter_can_be_filtered(self):
        self.validated["querystring"]["_fields"] = ["orig.foo"]
        obj = self.resource.get()
        self.assertIn("orig", obj["data"])
        self.assertIn("foo", obj["data"]["orig"])
        self.assertNotIn("other", obj["data"])
        self.assertNotIn("bar", obj["data"]["orig"])
        self.assertNotIn("nested", obj["data"]["orig"])

    def test_nested_parameter_can_be_filtered_on_multiple_levels(self):
        self.validated["querystring"]["_fields"] = ["orig.nested.size"]
        obj = self.resource.get()
        self.assertIn("nested", obj["data"]["orig"])
        self.assertIn("size", obj["data"]["orig"]["nested"])
        self.assertNotIn("hash", obj["data"]["orig"]["nested"])
        self.assertNotIn("mime", obj["data"]["orig"]["nested"])

    def test_can_filter_on_several_nested_fields(self):
        self.validated["querystring"]["_fields"] = ["orig.nested.size", "orig.nested.hash"]
        obj = self.resource.get()
        self.assertIn("size", obj["data"]["orig"]["nested"])
        self.assertIn("hash", obj["data"]["orig"]["nested"])
        self.assertNotIn("mime", obj["data"]["orig"]["nested"])


class PermissionTest(PartialResponseBase):
    resource_class = Resource

    def test_permissions_are_not_displayed(self):
        self.validated["querystring"]["_fields"] = ["field"]
        result = self.resource.get()
        self.assertNotIn("permissions", result)
