from bravado_core.request import IncomingRequest, unmarshal_request

from .support import SwaggerTest, MINIMALIST_RECORD


class SwaggerRecordRequestsTest(SwaggerTest):

    def setUp(self):
        super(SwaggerRecordRequestsTest, self).setUp()

        self.request = IncomingRequest()
        self.request.path = {
            'bucket_id': 'b1',
            'collection_id': 'c1',
            'record_id': 'r1',
        }
        self.request.query = {}
        self.request.json = lambda: MINIMALIST_RECORD

    def test_get_record(self):
        op = self.resources['Records'].get_record
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_create_record(self):
        op = self.resources['Records'].create_record
        params = unmarshal_request(self.request, op)
        self.app.post_json(op.path_name.format(**params),
                           self.request.json(), headers=self.headers)

    def test_update_record(self):
        op = self.resources['Records'].update_record
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_patch_record(self):
        op = self.resources['Records'].patch_record
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_delete_record(self):
        op = self.resources['Records'].delete_record
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)

    def test_get_records(self):
        op = self.resources['Records'].get_records
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_delete_records(self):
        op = self.resources['Records'].delete_records
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)
