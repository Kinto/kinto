from .support import SwaggerTest


class SwaggerPluginsTest(SwaggerTest):

    def test_get_history(self):
        op = self.resources['History'].get_histories
        self.request.path = {
            'bucket_id': 'b1',
        }
        self.validate_request_call(op)

    def test_delete_history(self):
        op = self.resources['History'].delete_histories
        self.request.path = {
            'bucket_id': 'b1',
        }
        self.validate_request_call(op)
