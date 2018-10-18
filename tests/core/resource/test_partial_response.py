from pyramid import httpexceptions

from kinto.core.resource import ShareableResource

from . import BaseTest


class PartialResponseBase(BaseTest):
    def setUp(self):
        super().setUp()
        self.resource._get_known_fields = lambda: ["field", "other", "orig"]
        self.object = self.model.create_object(
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
        self.resource.object_id = self.object["id"]
        self.resource.request = self.get_request()
        self.resource.request.validated = self.validated
        self.validated["querystring"] = {}


class PartialFieldsTest(PartialResponseBase):
    def test_fields_parameter_do_projection_on_get(self):
        self.validated["querystring"]["_fields"] = ["field"]
        object = self.resource.get()
        self.assertIn("field", object["data"])
        self.assertNotIn("other", object["data"])

    def test_fields_parameter_do_projection_on_get_all(self):
        self.validated["querystring"]["_fields"] = ["field"]
        object = self.resource.collection_get()["data"][0]
        self.assertIn("field", object)
        self.assertNotIn("other", object)

    def test_fail_if_fields_parameter_is_invalid(self):
        self.validated["querystring"]["_fields"] = "invalid_field"
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.get)
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.collection_get)

    def test_can_have_multiple_fields(self):
        self.validated["querystring"]["_fields"] = ["field", "other"]
        object = self.resource.get()
        self.assertIn("field", object["data"])
        self.assertIn("other", object["data"])

    def test_id_and_last_modified_are_not_filtered(self):
        self.validated["querystring"]["_fields"] = ["field"]
        object = self.resource.get()
        self.assertIn("id", object["data"])
        self.assertIn("last_modified", object["data"])

    def test_nested_parameter_can_be_filtered(self):
        self.validated["querystring"]["_fields"] = ["orig.foo"]
        object = self.resource.get()
        self.assertIn("orig", object["data"])
        self.assertIn("foo", object["data"]["orig"])
        self.assertNotIn("other", object["data"])
        self.assertNotIn("bar", object["data"]["orig"])
        self.assertNotIn("nested", object["data"]["orig"])

    def test_nested_parameter_can_be_filtered_on_multiple_levels(self):
        self.validated["querystring"]["_fields"] = ["orig.nested.size"]
        object = self.resource.get()
        self.assertIn("nested", object["data"]["orig"])
        self.assertIn("size", object["data"]["orig"]["nested"])
        self.assertNotIn("hash", object["data"]["orig"]["nested"])
        self.assertNotIn("mime", object["data"]["orig"]["nested"])

    def test_can_filter_on_several_nested_fields(self):
        self.validated["querystring"]["_fields"] = ["orig.nested.size", "orig.nested.hash"]
        object = self.resource.get()
        self.assertIn("size", object["data"]["orig"]["nested"])
        self.assertIn("hash", object["data"]["orig"]["nested"])
        self.assertNotIn("mime", object["data"]["orig"]["nested"])


class PermissionTest(PartialResponseBase):
    resource_class = ShareableResource

    def test_permissions_are_not_displayed(self):
        self.validated["querystring"]["_fields"] = ["field"]
        result = self.resource.get()
        self.assertNotIn("permissions", result)
