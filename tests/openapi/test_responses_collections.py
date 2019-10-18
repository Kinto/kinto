from bravado_core.response import validate_response

from .support import MINIMALIST_COLLECTION, OpenAPITest


class OpenAPICollectionResponsesTest(OpenAPITest):
    def test_get_collection_200(self):
        response = self.app.get("/buckets/b1/collections/c1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].get_collection
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_collection_200(self):
        response = self.app.post_json(
            "/buckets/b1/collections", self.collection, headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].create_collection
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_collection_201(self):
        response = self.app.post_json(
            "/buckets/b1/collections", MINIMALIST_COLLECTION, headers=self.headers, status=201
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].create_collection
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_put_collection_200(self):
        response = self.app.put_json(
            "/buckets/b1/collections/c1", MINIMALIST_COLLECTION, headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].update_collection
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_put_collection_201(self):
        response = self.app.put_json(
            "/buckets/b1/collections/c2", MINIMALIST_COLLECTION, headers=self.headers, status=201
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].update_collection
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_delete_collection_200(self):
        response = self.app.delete("/buckets/b1/collections/c1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].delete_collection
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_get_collections_200(self):
        response = self.app.get("/buckets/b1/collections", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].get_collections
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_delete_collections_200(self):
        response = self.app.delete("/buckets/b1/collections", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].delete_collections
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)
