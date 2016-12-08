from bravado_core.request import IncomingRequest, unmarshal_request
from bravado_core.swagger20_validator import ValidationError

from .support import SwaggerTest


class SwaggerRequestsValidationTest(SwaggerTest):

    def setUp(self):
        super(SwaggerRequestsValidationTest, self).setUp()

        self.request = IncomingRequest()
        self.request.path = {}
        self.request.query = {}
        self.request._json = {}
        self.request.json = lambda: self.request._json

    def test_validate_bucket_path(self):
        self.assertRaises(ValidationError, unmarshal_request,
                          self.request, self.resources['Buckets'].get_bucket)

    def test_validate_groups_path(self):
        self.assertRaises(ValidationError, unmarshal_request,
                          self.request, self.resources['Groups'].get_groups)

    def test_validate_group_path(self):
        paths = [
            {},
            {'bucket_id': 'b1'},
            {'group_id': 'g1'}
        ]
        for path in paths:
            self.request.path = path
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Groups'].get_group)

    def test_validate_collections_path(self):
        self.assertRaises(ValidationError, unmarshal_request,
                          self.request, self.resources['Collections'].get_collections)

    def test_validate_collection_path(self):
        paths = [
            {},
            {'bucket_id': 'b1'},
            {'collection_id': 'c1'}
        ]
        for path in paths:
            self.request.path = path
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Collections'].get_collection)

    def test_validate_records_path(self):
        paths = [
            {},
            {'bucket_id': 'b1'},
            {'collection_id': 'c1'}
        ]
        for path in paths:
            self.request.path = path
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Records'].get_records)

    def test_validate_record_path(self):
        paths = [
            {},
            {'bucket_id': 'b1', 'collection_id': 'c1'},
            {'record_id': 'r1'},
        ]
        for path in paths:
            self.request.path = path
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Records'].get_record)

    def test_validate_data(self):
        bodies = [
            {'data': 'aaa'},
            {'data': {'id': False}}
        ]
        for body in bodies:
            self.request._json = body
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Buckets'].create_bucket)

    def test_validate_permissions(self):
        bodies = [
            {'permissions': 'aaa'},
            {'permissions': {'read': 'aaa'}},
            {'permissions': {'read': [111]}},
        ]
        for body in bodies:
            self.request._json = body
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Buckets'].create_bucket)

    def test_validate_queries(self):
        queries = [
            {'_since': 'aaa'},
            {'_before': 'aaa'},
            {'_limit': 'aaa'},
            {'_token': 'aaa'},
        ]
        for query in queries:
            self.request.query = query
            self.assertRaises(ValidationError, unmarshal_request,
                              self.request, self.resources['Buckets'].get_buckets)
