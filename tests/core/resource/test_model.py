from pyramid import httpexceptions

from . import BaseTest


class ModelTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.object = self.model.create_object({"field": "value"})

    def test_list_returns_all_objects_in_data(self):
        result = self.resource.plural_get()
        objects = result["data"]
        self.assertEqual(len(objects), 1)
        self.assertDictEqual(objects[0], self.object)


class CreateTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.resource.request.validated["body"] = {"data": {"field": "new"}}

    def test_new_objects_are_linked_to_owner(self):
        resp = self.resource.plural_post()["data"]
        object_id = resp["id"]
        self.model.get_object(object_id)  # not raising

    def test_create_object_returns_at_least_id_and_last_modified(self):
        obj = self.resource.plural_post()["data"]
        self.assertIn(self.resource.model.id_field, obj)
        self.assertIn(self.resource.model.modified_field, obj)
        self.assertIn("field", obj)


class DeleteModelTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.patch_known_field.start()
        self.model.create_object({"field": "a"})
        self.model.create_object({"field": "b"})

    def test_delete_on_list_removes_all_objects(self):
        self.resource.plural_delete()
        result = self.resource.plural_get()
        objects = result["data"]
        self.assertEqual(len(objects), 0)

    def test_delete_returns_deleted_version_of_objects(self):
        result = self.resource.plural_delete()
        deleted = result["data"][0]
        self.assertIn("deleted", deleted)

    def test_plural_delete_supports_filters(self):
        self.resource.request.validated["querystring"] = {"field": "a"}
        self.resource.plural_delete()
        self.resource.request.validated["querystring"] = {}
        result = self.resource.plural_get()
        objects = result["data"]
        self.assertEqual(len(objects), 1)


class IsolatedModelsTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.resource.request.validated = {"header": {}, "querystring": {}}
        self.stored = self.model.create_object({}, parent_id="bob")
        self.resource.object_id = self.stored["id"]

    def get_request(self):
        request = super().get_request()
        request.prefixed_userid = "basicauth:alice"
        return request

    def get_context(self):
        context = super().get_context()
        context.prefixed_userid = "basicauth:alice"
        return context

    def test_list_is_filtered_by_user(self):
        resp = self.resource.plural_get()
        objects = resp["data"]
        self.assertEqual(len(objects), 0)

    def test_update_object_of_another_user_will_create_it(self):
        self.resource.request.validated["body"] = {"data": {"some": "object"}}
        self.resource.put()
        self.model.get_object(
            object_id=self.stored["id"], parent_id="basicauth:alice"
        )  # not raising

    def test_cannot_modify_object_of_other_user(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.patch)

    def test_cannot_delete_object_of_other_user(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.delete)
