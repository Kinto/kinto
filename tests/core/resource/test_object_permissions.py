from unittest import mock

from pyramid import httpexceptions

from kinto.core.permission.memory import Permission
from kinto.core.resource import Resource

from . import BaseTest


class PermissionTest(BaseTest):
    resource_class = Resource

    def setUp(self):
        self.permission = Permission()
        super().setUp()

    def get_request(self):
        request = super().get_request()
        request.registry.permission = self.permission
        return request


class PluralEndpointPermissionTest(PermissionTest):
    def setUp(self):
        super().setUp()
        self.result = self.resource.plural_get()

    def test_permissions_are_not_provided_in_plural_get(self):
        self.assertNotIn("permissions", self.result)

    def test_permissions_are_not_provided_in_plural_delete(self):
        result = self.resource.plural_delete()
        self.assertNotIn("permissions", result)


class ObtainObjectPermissionTest(PermissionTest):
    def setUp(self):
        super().setUp()
        obj = self.resource.model.create_object({})
        object_id = obj["id"]
        object_uri = "/articles/{}".format(object_id)
        self.permission.add_principal_to_ace(object_uri, "read", "basicauth:bob")
        self.permission.add_principal_to_ace(object_uri, "read", "account:readonly")
        self.permission.add_principal_to_ace(object_uri, "write", "basicauth:bob")
        self.resource.object_id = object_id
        self.resource.request.validated["body"] = {"data": {}}
        self.resource.request.path = object_uri

    def test_permissions_are_provided_in_object_get(self):
        result = self.resource.get()
        self.assertIn("permissions", result)

    def test_permissions_are_provided_in_object_put(self):
        result = self.resource.put()
        self.assertIn("permissions", result)

    def test_permissions_are_provided_in_object_patch(self):
        result = self.resource.patch()
        self.assertIn("permissions", result)

    def test_permissions_are_not_provided_in_object_delete(self):
        result = self.resource.delete()
        self.assertNotIn("permissions", result)

    def test_permissions_gives_lists_of_principals_per_ace(self):
        result = self.resource.get()
        permissions = result["permissions"]
        self.assertEqual(sorted(permissions["read"]), ["account:readonly", "basicauth:bob"])
        self.assertEqual(sorted(permissions["write"]), ["basicauth:bob"])

    def test_permissions_are_hidden_if_user_has_only_read_permission(self):
        self.resource.model.current_principal = "account:readonly"
        self.resource.model.prefixed_principals = []
        result = self.resource.get()
        self.assertEqual(result["permissions"], {})


class SpecifyObjectPermissionTest(PermissionTest):
    def setUp(self):
        super().setUp()
        self.obj = self.resource.model.create_object({})
        object_id = self.obj["id"]
        self.object_uri = "/articles/{}".format(object_id)
        self.permission.add_principal_to_ace(self.object_uri, "read", "account:readonly")
        self.resource.request.matchdict["id"] = object_id
        self.resource.request.validated["body"] = {"data": {}}
        self.resource.request.path = self.object_uri

    def test_write_permission_is_given_to_creator_on_post(self):
        self.resource.context.object_uri = "/articles"
        self.resource.request.method = "POST"
        result = self.resource.plural_post()
        self.assertEqual(sorted(result["permissions"]["write"]), ["basicauth:bob"])

    def test_write_permission_is_given_to_put(self):
        self.resource.request.method = "PUT"
        result = self.resource.put()
        permissions = result["permissions"]
        self.assertEqual(sorted(permissions["write"]), ["basicauth:bob"])

    def test_write_permission_is_given_to_anonymous(self):
        request = self.get_request()
        # Simulate an anonymous PUT
        request.method = "PUT"
        request.validated = {**self.resource.request.validated, "body": {"data": {**self.obj}}}
        request.prefixed_userid = None
        request.matchdict = {"id": self.obj["id"]}
        resource = self.resource_class(request=request, context=self.get_context())
        result = resource.put()
        self.assertIn("system.Everyone", result["permissions"]["write"])

    def test_permissions_can_be_specified_in_plural_post(self):
        perms = {"write": ["jean-louis"]}
        self.resource.request.method = "POST"
        self.resource.context.object_uri = "/articles"
        self.resource.request.validated["body"] = {"data": {}, "permissions": perms}
        result = self.resource.plural_post()
        self.assertEqual(sorted(result["permissions"]["write"]), ["basicauth:bob", "jean-louis"])

    def test_permissions_are_replaced_with_put(self):
        perms = {"write": ["jean-louis"]}
        self.resource.request.validated["body"]["permissions"] = perms
        self.resource.request.method = "PUT"
        result = self.resource.put()
        # In setUp() 'read' was set on this object.
        # PUT had got rid of it:
        self.assertNotIn("read", result["permissions"])

    def test_permissions_are_modified_with_patch(self):
        perms = {"write": ["jean-louis"]}
        self.resource.request.validated["body"] = {"permissions": perms}
        self.resource.request.method = "PATCH"
        result = self.resource.patch()
        permissions = result["permissions"]
        self.assertEqual(sorted(permissions["read"]), ["account:readonly"])
        self.assertEqual(sorted(permissions["write"]), ["basicauth:bob", "jean-louis"])

    def test_permissions_can_be_removed_with_patch_but_keep_current_user(self):
        self.permission.add_principal_to_ace(self.object_uri, "write", "jean-louis")

        perms = {"write": []}
        self.resource.request.validated["body"] = {"permissions": perms}
        self.resource.request.method = "PATCH"
        result = self.resource.patch()
        permissions = result["permissions"]
        self.assertEqual(sorted(permissions["read"]), ["account:readonly"]),
        self.assertEqual(sorted(permissions["write"]), ["basicauth:bob"])

    def test_permissions_can_be_removed_with_patch(self):
        self.permission.add_principal_to_ace(self.object_uri, "write", "jean-louis")

        perms = {"read": []}
        self.resource.request.validated["body"] = {"permissions": perms}
        self.resource.request.method = "PATCH"
        result = self.resource.patch()
        self.assertNotIn("read", result["permissions"])
        self.assertEqual(sorted(result["permissions"]["write"]), ["basicauth:bob", "jean-louis"])

    def test_412_errors_do_not_put_permission_in_object(self):
        self.resource.request.validated["header"] = {"If-Match": 1234567}  # invalid
        try:
            self.resource.put()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertEqual(
            error.json["details"]["existing"],
            {"id": self.obj["id"], "last_modified": self.obj["last_modified"]},
        )


class DeletedObjectPermissionTest(PermissionTest):
    def setUp(self):
        super().setUp()
        obj = self.resource.model.create_object({})
        self.resource.object_id = object_id = obj["id"]
        self.object_uri = "/articles/{}".format(object_id)
        self.resource.request.route_path.return_value = self.object_uri
        self.resource.request.path = self.object_uri
        self.permission.add_principal_to_ace(self.object_uri, "read", "fxa:user")

    def test_permissions_are_deleted_when_object_is_deleted(self):
        self.resource.delete()
        principals = self.permission.get_object_permission_principals(self.object_uri, "read")
        self.assertEqual(len(principals), 0)

    def test_permissions_are_deleted_when_plural_is_deleted(self):
        self.resource.context.on_plural_endpoint = True
        self.resource.plural_delete()
        principals = self.permission.get_object_permission_principals(self.object_uri, "read")
        self.assertEqual(len(principals), 0)


class GuestPluralEndpointTest(PermissionTest):
    def setUp(self):
        super().setUp()
        object1 = self.resource.model.create_object({"letter": "a"})
        object2 = self.resource.model.create_object({"letter": "b"})
        object3 = self.resource.model.create_object({"letter": "c"})

        uri1 = "/articles/{}".format(object1["id"])
        uri2 = "/articles/{}".format(object2["id"])
        uri3 = "/articles/{}".format(object3["id"])

        self.permission.add_principal_to_ace(uri1, "read", "fxa:user")
        self.permission.add_principal_to_ace(uri2, "read", "group")
        self.permission.add_principal_to_ace(uri3, "read", "jean-louis")

        self.resource.context.shared_ids = [object1["id"], object2["id"]]

    def test_plural_is_filtered_for_current_guest(self):
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 2)

    def test_guest_plural_get_can_be_filtered(self):
        self.resource.request.validated["querystring"] = {"letter": "a"}
        with mock.patch.object(self.resource, "is_known_field"):
            result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 1)

    def test_guest_plural_get_is_empty_if_no_object_is_shared(self):
        self.resource.context.shared_ids = ["tata lili"]
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_permission_backend_is_not_queried_if_not_guest(self):
        self.resource.context.shared_ids = None
        self.resource.request.registry.permission = None  # would fail!
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 3)

    def test_unauthorized_error_if_resource_does_not_exist(self):
        pass


class GuestPluralDeleteTest(PermissionTest):
    def setUp(self):
        super().setUp()
        object1 = self.resource.model.create_object({"letter": "a"})
        object2 = self.resource.model.create_object({"letter": "b"})
        object3 = self.resource.model.create_object({"letter": "c"})
        object4 = self.resource.model.create_object({"letter": "d"})

        uri1 = "/articles/{}".format(object1["id"])
        uri2 = "/articles/{}".format(object2["id"])
        uri3 = "/articles/{}".format(object3["id"])
        uri4 = "/articles/{}".format(object4["id"])

        self.permission.add_principal_to_ace(uri1, "read", "fxa:user")
        self.permission.add_principal_to_ace(uri2, "write", "fxa:user")
        self.permission.add_principal_to_ace(uri3, "write", "group")
        self.permission.add_principal_to_ace(uri4, "write", "jean-louis")

        self.resource.context.shared_ids = [object2["id"], object3["id"]]
        self.resource.request.method = "DELETE"

    def get_request(self):
        request = super().get_request()
        # RouteFactory must be aware of DELETE to query 'write' permission.
        request.method = "DELETE"
        return request

    def test_plural_is_filtered_for_current_guest(self):
        self.resource.request.path = "/articles"
        result = self.resource.plural_delete()
        self.assertEqual(len(result["data"]), 2)

    def test_guest_plural_delete_can_be_filtered(self):
        self.resource.request.validated["querystring"] = {"letter": "b"}
        with mock.patch.object(self.resource, "is_known_field"):
            result = self.resource.plural_delete()
        self.assertEqual(len(result["data"]), 1)
        objects = self.resource.model.get_objects()
        self.assertEqual(len(objects), 3)

    def test_guest_cannot_delete_objects_if_not_allowed(self):
        self.resource.context.shared_ids = ["tata lili"]
        result = self.resource.plural_delete()
        self.assertEqual(len(result["data"]), 0)
        objects = self.resource.model.get_objects()
        self.assertEqual(len(objects), 4)
