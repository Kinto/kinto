from bravado_core.response import validate_response

from .support import MINIMALIST_RECORD, OpenAPITest


class OpenAPIRecordResponsesTest(OpenAPITest):
    def test_get_record_200(self):
        response = self.app.get(
            "/buckets/b1/collections/c1/records/r1", headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].get_record
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_record_200(self):
        response = self.app.post_json(
            "/buckets/b1/collections/c1/records", self.record, headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].create_record
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_post_record_201(self):
        response = self.app.post_json(
            "/buckets/b1/collections/c1/records",
            MINIMALIST_RECORD,
            headers=self.headers,
            status=201,
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].create_record
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_put_record_200(self):
        response = self.app.put_json(
            "/buckets/b1/collections/c1/records/r1",
            MINIMALIST_RECORD,
            headers=self.headers,
            status=200,
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].update_record
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_put_record_201(self):
        response = self.app.put_json(
            "/buckets/b1/collections/c1/records/r2",
            MINIMALIST_RECORD,
            headers=self.headers,
            status=201,
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].update_record
        schema = self.spec.deref(op.op_spec["responses"]["201"])
        validate_response(schema, op, response)

    def test_delete_record_200(self):
        response = self.app.delete(
            "/buckets/b1/collections/c1/records/r1", headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].delete_record
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_get_records_200(self):
        response = self.app.get(
            "/buckets/b1/collections/c1/records", headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].get_records
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)

    def test_delete_records_200(self):
        response = self.app.delete(
            "/buckets/b1/collections/c1/records", headers=self.headers, status=200
        )
        response = self.cast_bravado_response(response)
        op = self.resources["Records"].delete_records
        schema = self.spec.deref(op.op_spec["responses"]["200"])
        validate_response(schema, op, response)
