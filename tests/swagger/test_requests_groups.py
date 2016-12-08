
from bravado_core.request import IncomingRequest, unmarshal_request

from .support import SwaggerTest, MINIMALIST_GROUP


class SwaggerGroupRequestsTest(SwaggerTest):

    def setUp(self):
        super(SwaggerGroupRequestsTest, self).setUp()

        self.request = IncomingRequest()
        self.request.path = {
            'bucket_id': 'b1',
            'group_id': 'g1',
        }
        self.request.query = {}
        self.request.json = lambda: MINIMALIST_GROUP

    def test_get_group(self):
        op = self.resources['Groups'].get_group
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_create_group(self):
        op = self.resources['Groups'].create_group
        params = unmarshal_request(self.request, op)
        self.app.post_json(op.path_name.format(**params),
                           self.request.json(), headers=self.headers)

    def test_update_group(self):
        op = self.resources['Groups'].update_group
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_patch_group(self):
        op = self.resources['Groups'].patch_group
        params = unmarshal_request(self.request, op)
        self.app.put_json(op.path_name.format(**params),
                          self.request.json(), headers=self.headers)

    def test_delete_group(self):
        op = self.resources['Groups'].delete_group
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)

    def test_get_groups(self):
        op = self.resources['Groups'].get_groups
        params = unmarshal_request(self.request, op)
        self.app.get(op.path_name.format(**params), headers=self.headers)

    def test_delete_groups(self):
        op = self.resources['Groups'].delete_groups
        params = unmarshal_request(self.request, op)
        self.app.delete(op.path_name.format(**params), headers=self.headers)
