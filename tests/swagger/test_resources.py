import json

from bravado_core.request import unmarshal_request
from bravado_core.response import validate_response

from .support import (SwaggerTest, MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class SwaggerResourcesTest(SwaggerTest):

    allowed_failures = ['version']

    def test_existing_path(self):
        for resource in self.resources.values():
            for op_id, op in resource.operations.items():
                self.setUp()
                self.request.path = {
                    'bucket_id': 'b1',
                    'group_id': 'g1',
                    'collection_id': 'c1',
                    'record_id': 'r1'
                }
                resp = self.validate_request_call(op, expect_errors=True)

                if op_id not in self.allowed_failures:
                    # Method must exist (404 and 405 means it might not exist)
                    self.assertIn(resp.status_int, [200, 201, 400])

    def test_resource_utilities(self):
        resource = self.resources['Utilities']
        for op_id, op in resource.operations.items():
                if op_id not in self.allowed_failures:
                    self.validate_request_call(op)

    def test_resource_batch(self):
        resource = self.resources['Batch']
        for op in resource.operations.values():
            self.setUp()
            requests = [{'path': '/v1/buckets'}]
            defaults = {'method': 'POST'}
            self.request.json = lambda: dict(
                requests=requests,
                defaults=defaults
            )
            self.validate_request_call(op)

    def test_resource_buckets(self):
        resource = self.resources['Buckets']

        for op in resource.operations.values():
            self.setUp()
            self.request.path = {
                'bucket_id': 'b1',
            }
            self.request.json = lambda: MINIMALIST_BUCKET
            self.validate_request_call(op)

    def test_resource_groups(self):
        resource = self.resources['Groups']

        for op in resource.operations.values():
            self.setUp()
            self.request.path = {
                'bucket_id': 'b1',
                'group_id': 'g1',
            }
            self.request.json = lambda: MINIMALIST_GROUP
            self.validate_request_call(op)

    def test_resource_collections(self):
        resource = self.resources['Collections']

        for op in resource.operations.values():
            self.setUp()
            self.request.path = {
                'bucket_id': 'b1',
                'collection_id': 'c1',
            }
            self.request.json = lambda: MINIMALIST_COLLECTION
            self.validate_request_call(op)

    def test_resource_records(self):
        resource = self.resources['Records']

        for op in resource.operations.values():
            self.setUp()
            self.request.path = {
                'bucket_id': 'b1',
                'collection_id': 'c1',
                'record_id': 'r1',
            }
            self.request.json = lambda: MINIMALIST_RECORD
            self.validate_request_call(op)

    def validate_request_call(self, op, **kargs):
        params = unmarshal_request(self.request, op)
        response = self.app.request(op.path_name.format(**params),
                                    body=json.dumps(self.request.json()).encode(),
                                    method=op.http_method.upper(),
                                    headers=self.headers, **kargs)
        schema = self.spec.deref(op.op_spec['responses'][str(response.status_code)])
        casted_resp = self.cast_bravado_response(response)
        validate_response(schema, op, casted_resp)
        return response
