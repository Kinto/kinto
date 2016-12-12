from bravado_core.request import IncomingRequest, unmarshal_request

from .support import SwaggerTest, MINIMALIST_COLLECTION


class SwaggerCollectionRequestsTest(SwaggerTest):

    def setUp(self):
        super(SwaggerCollectionRequestsTest, self).setUp()

        self.request = IncomingRequest()
        self.request.path = {
            'bucket_id': 'b1',
            'collection_id': 'c1',
        }
        self.request.headers = {}
        self.request.query = {}
        self.request.json = lambda: MINIMALIST_COLLECTION

    def test_get_collection(self):
        op = self.resources['Collections'].get_collection
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_create_collection(self):
        op = self.resources['Collections'].create_collection
        params = unmarshal_request(self.request, op)
        self.app.post_json(op.path_name.format(**params),
                           self.request.json(), headers=self.headers)

    def test_update_collection(self):
        op = self.resources['Collections'].update_collection
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_patch_collection(self):
        op = self.resources['Collections'].patch_collection
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_delete_collection(self):
        op = self.resources['Collections'].delete_collection
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)

    def test_get_collections(self):
        op = self.resources['Collections'].get_collections
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_delete_collections(self):
        op = self.resources['Collections'].delete_collections
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)
