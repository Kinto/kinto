from .support import (OpenAPITest, MINIMALIST_BUCKET, MINIMALIST_GROUP,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class OpenAPIResourcesTest(OpenAPITest):

    allowed_failures = ['version']

    def test_resource_utilities(self):
        resource = self.resources['Utilities']
        for op_id, op in resource.operations.items():
                if op_id not in self.allowed_failures:
                    self.validate_request_call(op)

    def test_resource_batch(self):
        resource = self.resources['Batch']
        for op in resource.operations.values():
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
            self.app.put_json('/buckets/b1',
                              MINIMALIST_BUCKET, headers=self.headers)
            self.request.path = {
                'id': 'b1',
            }
            bucket = {**MINIMALIST_BUCKET, 'data': {'foo': 'bar'}}
            self.request.json = lambda: bucket
            self.validate_request_call(op)

    def test_resource_groups(self):
        resource = self.resources['Groups']

        for op in resource.operations.values():
            self.app.put_json('/buckets/b1/groups/g1',
                              MINIMALIST_GROUP, headers=self.headers)
            self.request.path = {
                'bucket_id': 'b1',
                'id': 'g1',
            }
            self.request.json = lambda: MINIMALIST_GROUP
            self.validate_request_call(op)

    def test_resource_collections(self):
        resource = self.resources['Collections']

        for op in resource.operations.values():
            self.app.put_json('/buckets/b1/collections/c1',
                              MINIMALIST_COLLECTION, headers=self.headers)
            self.request.path = {
                'bucket_id': 'b1',
                'id': 'c1',
            }
            collection = {**MINIMALIST_COLLECTION, 'data': {'foo': 'bar'}}
            self.request.json = lambda: collection
            self.validate_request_call(op)

    def test_resource_records(self):
        resource = self.resources['Records']

        for op in resource.operations.values():
            self.app.put_json('/buckets/b1/collections/c1/records/r1',
                              MINIMALIST_RECORD, headers=self.headers)
            self.request.path = {
                'bucket_id': 'b1',
                'collection_id': 'c1',
                'id': 'r1',
            }
            self.request.json = lambda: MINIMALIST_RECORD
            self.validate_request_call(op)
