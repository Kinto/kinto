from bravado_core.response import validate_response

from .support import OpenAPITest, MINIMALIST_BUCKET


class OpenAPIBucketResponsesTest(OpenAPITest):
    def test_get_bucket_200(self):
        response = self.app.get("/buckets/b1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_bucket_200(self):
        response = self.app.post_json("/buckets", self.bucket, headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].create_bucket
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_bucket_201(self):
        response = self.app.post_json(
            "/buckets", MINIMALIST_BUCKET, headers=self.headers, status=201
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].create_bucket
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_put_bucket_200(self):
        response = self.app.put("/buckets/b1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_put_bucket_201(self):
        response = self.app.put("/buckets/b2", headers=self.headers, status=201)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_delete_bucket_200(self):
        response = self.app.delete("/buckets/b1", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_bucket
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_get_buckets_200(self):
        response = self.app.get("/buckets", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_buckets
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_delete_buckets_200(self):
        response = self.app.delete("/buckets", headers=self.headers, status=200)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_buckets
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)
