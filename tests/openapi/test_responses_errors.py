from bravado_core.response import validate_response

from kinto.core import testing
from .support import OpenAPITest
from ..support import MINIMALIST_BUCKET, MINIMALIST_GROUP, MINIMALIST_COLLECTION, MINIMALIST_RECORD


class OpenAPIObjectErrorResponsesTest(OpenAPITest):
    def setUp(self):
        super().setUp()

        self.bucket = self.app.put_json(
            "/buckets/b1", MINIMALIST_BUCKET, headers=self.headers
        ).json

        self.group = self.app.put_json(
            "/buckets/b1/groups/g1", MINIMALIST_GROUP, headers=self.headers
        ).json

        self.collection = self.app.put_json(
            "/buckets/b1/collections/c1", MINIMALIST_COLLECTION, headers=self.headers
        ).json

        self.record = self.app.put_json(
            "/buckets/b1/collections/c1/records/r1", MINIMALIST_RECORD, headers=self.headers
        ).json

    def test_object_get_304(self):
        headers = {
            **self.headers,
            "If-None-Match": '"{}"'.format(self.bucket["data"]["last_modified"]),
        }
        response = self.app.get("/buckets/b1", headers=headers, status=304)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["304"])
        validate_response(schema, op, response)

    def test_object_get_400(self):
        headers = {**self.headers, "If-None-Match": "aaa"}
        response = self.app.get("/buckets/b1", headers=headers, status=400)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["400"])
        validate_response(schema, op, response)

    def test_object_get_401(self):
        response = self.app.get("/buckets/b1", status=401)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["401"])
        validate_response(schema, op, response)

    def test_object_get_403(self):
        headers = {**self.headers, **testing.get_user_headers("aaa")}
        response = self.app.get("/buckets/b1", headers=headers, status=403)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["403"])
        validate_response(schema, op, response)

    def test_object_get_404(self):
        response = self.app.get("/buckets/b1/collections/col", headers=self.headers, status=404)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].get_collection
        schema = self.spec.deref(op.op_spec["responses"]["404"])
        validate_response(schema, op, response)

    def test_object_get_406(self):
        headers = {**self.headers, "Accept": "text/html"}
        response = self.app.get("/buckets/b1", headers=headers, status=406)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["406"])
        validate_response(schema, op, response)

    def test_object_get_412(self):
        headers = {
            **self.headers,
            "If-Match": '"{}"'.format(self.bucket["data"]["last_modified"] - 1),
        }
        response = self.app.get("/buckets/b1", headers=headers, status=412)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_bucket
        schema = self.spec.deref(op.op_spec["responses"]["412"])
        validate_response(schema, op, response)

    def test_object_put_400(self):
        response = self.app.put_json("/buckets/b1", [], headers=self.headers, status=400)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["400"])
        validate_response(schema, op, response)

    def test_object_put_401(self):
        response = self.app.put_json("/buckets/b1", MINIMALIST_BUCKET, status=401)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["401"])
        validate_response(schema, op, response)

    def test_object_put_403(self):
        headers = {**self.headers, **testing.get_user_headers("aaa")}
        response = self.app.put_json("/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=403)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["403"])
        validate_response(schema, op, response)

    def test_object_put_406(self):
        headers = {**self.headers, "Accept": "text/html"}
        response = self.app.put_json("/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=406)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["406"])
        validate_response(schema, op, response)

    def test_object_put_412(self):
        headers = {
            **self.headers,
            "If-Match": '"{}"'.format(self.bucket["data"]["last_modified"] - 1),
        }
        response = self.app.put_json("/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=412)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["412"])
        validate_response(schema, op, response)

    def test_object_put_415(self):
        headers = {**self.headers, "Content-Type": "text/html"}
        response = self.app.put_json("/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=415)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].update_bucket
        schema = self.spec.deref(op.op_spec["responses"]["415"])
        validate_response(schema, op, response)

    def test_object_patch_400(self):
        response = self.app.patch_json("/buckets/b1", [], headers=self.headers, status=400)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].patch_bucket
        schema = self.spec.deref(op.op_spec["responses"]["400"])
        validate_response(schema, op, response)

    def test_object_patch_401(self):
        response = self.app.patch_json("/buckets/b1", MINIMALIST_BUCKET, status=401)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].patch_bucket
        schema = self.spec.deref(op.op_spec["responses"]["401"])
        validate_response(schema, op, response)

    def test_object_patch_403(self):
        headers = {**self.headers, **testing.get_user_headers("aaa")}
        response = self.app.patch_json(
            "/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=403
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].patch_bucket
        schema = self.spec.deref(op.op_spec["responses"]["403"])
        validate_response(schema, op, response)

    def test_object_patch_404(self):
        response = self.app.patch_json(
            "/buckets/b1/collections/col", MINIMALIST_COLLECTION, headers=self.headers, status=404
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].patch_collection
        schema = self.spec.deref(op.op_spec["responses"]["404"])
        validate_response(schema, op, response)

    def test_object_patch_406(self):
        headers = {**self.headers, "Accept": "text/html"}
        response = self.app.patch_json(
            "/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=406
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].patch_bucket
        schema = self.spec.deref(op.op_spec["responses"]["406"])
        validate_response(schema, op, response)

    def test_object_patch_412(self):
        headers = {
            **self.headers,
            "If-Match": '"{}"'.format(self.bucket["data"]["last_modified"] - 1),
        }
        response = self.app.patch_json(
            "/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=412
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].patch_bucket
        schema = self.spec.deref(op.op_spec["responses"]["412"])
        validate_response(schema, op, response)

    def test_object_patch_415(self):
        headers = {**self.headers, "Content-Type": "text/html"}
        response = self.app.patch_json(
            "/buckets/b1", MINIMALIST_BUCKET, headers=headers, status=415
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].patch_bucket
        schema = self.spec.deref(op.op_spec["responses"]["415"])
        validate_response(schema, op, response)

    def test_object_delete_400(self):
        headers = {**self.headers, "If-Match": "aaa"}
        response = self.app.delete("/buckets/b1", headers=headers, status=400)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_bucket
        schema = self.spec.deref(op.op_spec["responses"]["400"])
        validate_response(schema, op, response)

    def test_object_delete_401(self):
        response = self.app.delete("/buckets/b1", status=401)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_bucket
        schema = self.spec.deref(op.op_spec["responses"]["401"])
        validate_response(schema, op, response)

    def test_object_delete_403(self):
        headers = {**self.headers, **testing.get_user_headers("aaa")}
        response = self.app.delete("/buckets/b1", headers=headers, status=403)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_bucket
        schema = self.spec.deref(op.op_spec["responses"]["403"])
        validate_response(schema, op, response)

    def test_object_delete_404(self):
        response = self.app.delete("/buckets/b1/collections/col", headers=self.headers, status=404)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].delete_collection
        schema = self.spec.deref(op.op_spec["responses"]["404"])
        validate_response(schema, op, response)

    def test_object_delete_406(self):
        headers = {**self.headers, "Accept": "text/html"}
        response = self.app.delete("/buckets/b1", headers=headers, status=406)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_bucket
        schema = self.spec.deref(op.op_spec["responses"]["406"])
        validate_response(schema, op, response)

    def test_object_delete_412(self):
        headers = {
            **self.headers,
            "If-Match": '"{}"'.format(self.bucket["data"]["last_modified"] - 1),
        }
        response = self.app.delete("/buckets/b1", headers=headers, status=412)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_bucket
        schema = self.spec.deref(op.op_spec["responses"]["412"])
        validate_response(schema, op, response)

    def test_list_get_304(self):
        headers = {
            **self.headers,
            "If-None-Match": '"{}"'.format(self.bucket["data"]["last_modified"]),
        }
        response = self.app.get("/buckets", headers=headers, status=304)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_buckets
        schema = self.spec.deref(op.op_spec["responses"]["304"])
        validate_response(schema, op, response)

    def test_list_get_400(self):
        response = self.app.get("/buckets?_since=aaa", headers=self.headers, status=400)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_buckets
        schema = self.spec.deref(op.op_spec["responses"]["400"])
        validate_response(schema, op, response)

    def test_list_get_401(self):
        response = self.app.get("/buckets", status=401)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_buckets
        schema = self.spec.deref(op.op_spec["responses"]["401"])
        validate_response(schema, op, response)

    def test_list_get_403(self):
        headers = {**self.headers, **testing.get_user_headers("aaa")}
        response = self.app.get("/buckets/b1/collections", headers=headers, status=403)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].get_collections
        schema = self.spec.deref(op.op_spec["responses"]["403"])
        validate_response(schema, op, response)

    def test_list_get_406(self):
        headers = {**self.headers, "Accept": "text/html"}
        response = self.app.get("/buckets", headers=headers, status=406)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_buckets
        schema = self.spec.deref(op.op_spec["responses"]["406"])
        validate_response(schema, op, response)

    def test_list_get_412(self):
        headers = {
            **self.headers,
            "If-Match": '"{}"'.format(self.bucket["data"]["last_modified"] - 1),
        }
        response = self.app.get("/buckets/b1", headers=headers, status=412)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].get_buckets
        schema = self.spec.deref(op.op_spec["responses"]["412"])
        validate_response(schema, op, response)

    def test_list_delete_401(self):
        response = self.app.delete("/buckets", status=401)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_buckets
        schema = self.spec.deref(op.op_spec["responses"]["401"])
        validate_response(schema, op, response)

    def test_list_delete_403(self):
        headers = {**self.headers, **testing.get_user_headers("aaa")}
        response = self.app.delete("/buckets/b1/collections", headers=headers, status=403)
        response = self.cast_bravado_response(response)
        op = self.resources["Collections"].delete_collections
        schema = self.spec.deref(op.op_spec["responses"]["403"])
        validate_response(schema, op, response)

    def test_list_delete_405(self):
        # XXX
        pass

    def test_list_delete_406(self):
        headers = {**self.headers, "Accept": "text/html"}
        response = self.app.delete("/buckets", headers=headers, status=406)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_buckets
        schema = self.spec.deref(op.op_spec["responses"]["406"])
        validate_response(schema, op, response)

    def test_list_delete_412(self):
        headers = {
            **self.headers,
            "If-Match": '"{}"'.format(self.bucket["data"]["last_modified"] - 1),
        }
        response = self.app.delete("/buckets", headers=headers, status=412)
        response = self.cast_bravado_response(response)
        op = self.resources["Buckets"].delete_buckets
        schema = self.spec.deref(op.op_spec["responses"]["412"])
        validate_response(schema, op, response)
