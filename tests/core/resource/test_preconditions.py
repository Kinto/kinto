from pyramid import httpexceptions

from kinto.core.errors import ERRORS

from . import BaseTest


class NotModifiedTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.stored = self.model.create_object({})

        self.resource = self.resource_class(request=self.get_request(), context=self.get_context())
        self.resource.request.validated = {**self.validated}
        self.resource.plural_get()
        self.validated = self.resource.request.validated
        current = self.last_response.headers["ETag"][1:-1]
        self.validated["header"]["If-None-Match"] = int(current)

    def test_plural_returns_200_if_change_meanwhile(self):
        self.validated["header"]["If-None-Match"] = 42
        self.resource.plural_get()  # Not raising.

    def test_plural_returns_304_if_no_change_meanwhile(self):
        try:
            self.resource.plural_get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertEqual(error.code, 304)
        self.assertIsNotNone(error.headers.get("ETag"))
        self.assertIsNotNone(error.headers.get("Last-Modified"))

    def test_single_object_returns_304_if_no_change_meanwhile(self):
        self.resource.object_id = self.stored["id"]
        try:
            self.resource.get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertEqual(error.code, 304)
        self.assertIsNotNone(error.headers.get("ETag"))
        self.assertIsNotNone(error.headers.get("Last-Modified"))

    def test_single_object_last_modified_is_returned(self):
        self.resource.timestamp = 0
        self.resource.object_id = self.stored["id"]
        try:
            self.resource.get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertNotIn("1970", error.headers["Last-Modified"])


class ModifiedMeanwhileTest(BaseTest):
    def setUp(self):
        super().setUp()

        # Create an object using model (will have an incremented last_modified)
        self.stored = self.model.create_object({})
        self.stored.pop(self.model.permissions_field)

        # Update the object we just created (will set last_modified with the server ETag)
        self.resource.object_id = self.stored["id"]
        self.resource.put()
        # Update our object with last_modified provided by the server
        self.stored["last_modified"] = int(self.last_response.headers["ETag"][1:-1])

        self.validated = self.resource.request.validated
        self.current = int(self.last_response.headers["ETag"][1:-1])
        previous = self.current - 10
        self.validated["header"]["If-Match"] = previous

    def test_preconditions_errors_are_json_formatted(self):
        try:
            self.resource.plural_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertEqual(
            error.json,
            {
                "errno": ERRORS.MODIFIED_MEANWHILE.value,
                "message": "Resource was modified meanwhile",
                "code": 412,
                "error": "Precondition Failed",
            },
        )

    def test_plural_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_get)

    def test_plural_returns_412_if_if_match_is_superior(self):
        self.validated["header"]["If-Match"] = self.current + 10
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_get)

    def test_plural_returns_200_if_if_match_is_equal(self):
        self.validated["header"]["If-Match"] = self.current
        self.resource.plural_get()

    def test_412_errors_on_plural_endpoint_do_not_provide_existing_object(self):
        try:
            self.resource.plural_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertNotIn("existing", error.json.get("details", {}))

    def test_412_on_plural_endpoint_has_last_modified_timestamp(self):
        try:
            self.resource.plural_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertIsNotNone(error.headers.get("ETag"))
        self.assertIsNotNone(error.headers.get("Last-Modified"))

    def test_412_errors_on_object_provide_existing_data(self):
        try:
            self.resource.put()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertDictEqual(error.json["details"]["existing"], self.stored)

    def test_single_object_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.get)

    def test_412_on_single_object_has_last_modified_timestamp(self):
        try:
            self.resource.get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertIsNotNone(error.headers.get("ETag"))
        self.assertIsNotNone(error.headers.get("Last-Modified"))

    def test_create_returns_412_if_changed_meanwhile(self):
        self.validated["body"] = {"data": {"field": "new"}}
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_post)

    def test_put_returns_412_if_changed_meanwhile(self):
        self.model.delete_object(self.stored)
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_put_returns_412_if_changed_and_none_match_present(self):
        self.validated["body"] = {"data": {"field": "new"}}
        self.validated["header"]["If-None-Match"] = 42
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_put_returns_last_modified_if_changed_meanwhile(self):
        self.resource.timestamp = 0
        self.resource.object_id = self.stored["id"]
        try:
            self.resource.put()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertNotIn("1970", error.headers["Last-Modified"])

    def test_put_returns_412_if_deleted_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_put_if_none_match_star_fails_if_object_exists(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_get_if_none_match_star_fails_if_object_exists(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.get)

    def test_put_if_none_match_star_succeeds_if_object_does_not_exist(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.validated["body"] = {"data": {"field": "new"}}
        self.resource.object_id = self.resource.model.id_generator()
        self.resource.put()  # not raising.

    def test_put_if_none_match_star_succeeds_if_tombstone_exists(self):
        self.model.delete_object(self.stored)
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.validated["body"] = {"data": {"field": "new"}}
        self.resource.put()  # not raising.

    def test_post_if_none_match_star_fails_if_object_exists(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.resource.request.json = {"data": {"id": self.stored["id"], "field": "new"}}
        self.validated["body"] = self.resource.request.json
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_post)

    def test_post_if_none_match_star_succeeds_if_object_does_not_exist(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.resource.object_id = self.resource.model.id_generator()
        self.validated["body"] = {"data": {"id": self.resource.object_id, "field": "new"}}
        self.resource.plural_post()  # not raising.

    def test_get_if_none_match_star_fails_on_plural_endpoints(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_get)

    def test_delete_if_none_match_star_fails_on_plural_endpoints(self):
        self.validated["header"].pop("If-Match")
        self.validated["header"]["If-None-Match"] = "*"
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_delete)

    def test_get_if_match_star_succeeds_if_object_exists(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.object_id = self.stored["id"]
        self.resource.get()

    def test_post_if_match_star_succeeds_if_object_exists(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.request.json = {"data": {"id": self.stored["id"], "field": "new"}}
        self.validated["body"] = self.resource.request.json
        self.resource.plural_post()

    def test_put_if_match_star_succeeds_if_object_exists(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.put()

    def test_patch_if_match_star_succeeds_if_object_exists(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.request.json = {"data": {"id": self.stored["id"], "field": "new"}}
        self.validated["body"] = self.resource.request.json
        self.resource.patch()

    def test_delete_if_match_star_succeeds_if_object_exists(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.delete()

    def test_put_if_match_star_fails_if_object_does_not_exist(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.request.json = {"data": {"field": "new"}}
        self.validated["body"] = self.resource.request.json
        self.resource.object_id = self.resource.model.id_generator()
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_put_if_match_current_fails_if_object_does_not_exist(self):
        self.validated["header"]["If-Match"] = self.current  # wouldn't raise on existing
        self.resource.request.json = {"data": {"field": "new"}}
        self.validated["body"] = self.resource.request.json
        self.resource.object_id = self.resource.model.id_generator()
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_put_if_fails_if_if_match_is_superior(self):
        self.validated["header"]["If-Match"] += self.current + 10
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.put)

    def test_get_if_match_star_suceed_on_plural_endpoints(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.plural_get()

    def test_delete_if_match_star_suceed_on_plural_endpoints(self):
        self.validated["header"]["If-Match"] = "*"
        self.resource.plural_delete()

    def test_patch_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.patch)

    def test_patch_returns_last_modified_if_changed_meanwhile(self):
        self.resource.timestamp = 0
        try:
            self.resource.patch()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertNotIn("1970", error.headers["Last-Modified"])

    def test_delete_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.delete)

    def test_delete_all_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed, self.resource.plural_delete)
