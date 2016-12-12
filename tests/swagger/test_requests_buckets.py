from bravado_core.request import IncomingRequest, unmarshal_request

from .support import SwaggerTest, MINIMALIST_BUCKET


class SwaggerBucketRequestsTest(SwaggerTest):

    def setUp(self):
        super(SwaggerBucketRequestsTest, self).setUp()

        self.request = IncomingRequest()
        self.request.path = {
            'bucket_id': 'b1',
        }
        self.request.headers = {}
        self.request.query = {}
        self.request.json = lambda: MINIMALIST_BUCKET

    def test_get_bucket(self):
        op = self.resources['Buckets'].get_bucket
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_create_bucket(self):
        op = self.resources['Buckets'].create_bucket
        params = unmarshal_request(self.request, op)
        self.app.post_json(op.path_name.format(**params),
                           self.request.json(), headers=self.headers)

    def test_update_bucket(self):
        op = self.resources['Buckets'].update_bucket
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_patch_bucket(self):
        op = self.resources['Buckets'].patch_bucket
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_delete_bucket(self):
        op = self.resources['Buckets'].delete_bucket
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)

    def test_get_buckets(self):
        op = self.resources['Buckets'].get_buckets
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_delete_buckets(self):
        op = self.resources['Buckets'].delete_buckets
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)
