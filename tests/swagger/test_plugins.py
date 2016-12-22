from .support import SwaggerTest


class SwaggerPluginsTest(SwaggerTest):

    def test_get_history(self):
        op = self.resources['History'].get_history
        self.request.path = {
            'bucket_id': 'b1',
        }
        self.validate_request_call(op)

    def test_delete_history(self):
        op = self.resources['History'].delete_history
        self.request.path = {
            'bucket_id': 'b1',
        }
        self.validate_request_call(op)

    def test_get_admin(self):
        op = self.resources['Admin'].admin
        self.app.get(op.path_name)
