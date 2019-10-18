from bravado_core.response import validate_response

from .support import MINIMALIST_GROUP, OpenAPITest


class OpenAPIGroupResponsesTest(OpenAPITest):
    def test_get_group_200(self):
        response = self.app.get("/buckets/b1/groups/g1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].get_group
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_group_200(self):
        response = self.app.post_json(
            "/buckets/b1/groups", self.group, headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].create_group
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_group_201(self):
        response = self.app.post_json(
            "/buckets/b1/groups", MINIMALIST_GROUP, headers=self.headers, status=201
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].create_group
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_put_group_200(self):
        response = self.app.put_json(
            "/buckets/b1/groups/g1", MINIMALIST_GROUP, headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].update_group
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_put_group_201(self):
        response = self.app.put_json(
            "/buckets/b1/groups/g2", MINIMALIST_GROUP, headers=self.headers, status=201
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].update_group
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_delete_group_200(self):
        response = self.app.delete("/buckets/b1/groups/g1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].delete_group
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_get_groups_200(self):
        response = self.app.get("/buckets/b1/groups", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].get_groups
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_delete_groups_200(self):
        response = self.app.delete("/buckets/b1/groups", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Groups"].delete_groups
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)
