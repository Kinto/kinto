from bravado_core.request import IncomingRequest, unmarshal_request
from bravado_core.swagger20_validator import ValidationError

from .support import OpenAPITest


class OpenAPIRequestsValidationTest(OpenAPITest):
    def setUp(self):
        super().setUp()

        self.request = IncomingRequest()
        self.request.path = {}
        self.request.headers = {}
        self.request.query = {}
        self.request._json = {}
        self.request.json = lambda: self.request._json

    def test_validate_bucket_path(self):
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Buckets"].get_bucket
        )

    def test_validate_groups_path(self):
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Groups"].get_groups
        )

    def test_validate_group_path(self):
        paths = [{}, {"bucket_id": "b1"}, {"id": "g1"}]
        for path in paths:
            self.request.path = path
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Groups"].get_group,
            )

    def test_validate_collections_path(self):
        self.assertRaises(
            ValidationError,
            unmarshal_request,
            self.request,
            self.resources["Collections"].get_collections,
        )

    def test_validate_plural_path(self):
        paths = [{}, {"bucket_id": "b1"}, {"id": "c1"}]
        for path in paths:
            self.request.path = path
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Collections"].get_collection,
            )

    def test_validate_records_path(self):
        paths = [{}, {"bucket_id": "b1"}, {"collection_id": "c1"}]
        for path in paths:
            self.request.path = path
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Records"].get_records,
            )

    def test_validate_object_path(self):
        paths = [{}, {"bucket_id": "b1", "collection_id": "c1"}, {"id": "r1"}]
        for path in paths:
            self.request.path = path
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Records"].get_record,
            )

    def test_validate_data(self):
        bodies = [{"data": "aaa"}]
        for body in bodies:
            self.request._json = body
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Buckets"].create_bucket,
            )

    def test_validate_permissions(self):
        bodies = [
            {"permissions": "aaa"},
            {"permissions": {"read": "aaa"}},
            {"permissions": {"read": [111]}},
        ]
        for body in bodies:
            self.request._json = body
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Buckets"].create_bucket,
            )

    def test_validate_queries(self):
        queries = [{"_since": "aaa"}, {"_before": "aaa"}, {"_limit": "aaa"}, {"_token": {}}]
        for query in queries:
            self.request.query = query
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Buckets"].get_buckets,
            )

    def test_validate_headers(self):
        headers = [{"If-None-Match": "123"}, {"If-Match": "123"}]
        for head in headers:
            self.request.headers = head
            self.assertRaises(
                ValidationError,
                unmarshal_request,
                self.request,
                self.resources["Buckets"].get_buckets,
            )

    def test_validate_batch_requests_method(self):
        self.request._json = {"requests": [{"method": "AAA", "path": "/buckets/b1"}]}
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_requests_path(self):
        self.request._json = {"requests": [{"method": "GET", "path": 123}]}
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_requests_body(self):
        self.request._json = {"requests": [{"method": "GET", "path": "/buckets/b1", "body": []}]}
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_requests_header(self):
        self.request._json = {
            "requests": [{"method": "GET", "path": "/buckets/b1", "body": {}, "headers": []}]
        }
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_defaults(self):
        self.request._json = {
            "defaults": [],
            "requests": [{"method": "GET", "path": "/buckets/b1"}],
        }
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_defaults_method(self):
        self.request._json = {"defaults": {"method": "AAA"}, "requests": [{"path": "/buckets/b1"}]}
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_defaults_body(self):
        self.request._json = {
            "defaults": {"body": []},
            "requests": [{"method": "PUT", "path": "/buckets/b1"}],
        }
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )

    def test_validate_batch_defaults_headers(self):
        self.request._json = {
            "defaults": {"headers": []},
            "requests": [{"method": "GET", "path": "/buckets/b1"}],
        }
        self.assertRaises(
            ValidationError, unmarshal_request, self.request, self.resources["Batch"].batch
        )
