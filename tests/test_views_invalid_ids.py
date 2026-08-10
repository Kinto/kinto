import unittest

from .support import MINIMALIST_BUCKET, MINIMALIST_COLLECTION, MINIMALIST_RECORD, BaseWebTest


class InvalidParentIdTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.app.put_json("/buckets/beers", MINIMALIST_BUCKET, headers=self.headers)
        self.app.put_json(
            "/buckets/beers/collections/barley", MINIMALIST_COLLECTION, headers=self.headers
        )
        self.app.put_json(
            "/buckets/beers/collections/barley/records/wheat",
            MINIMALIST_RECORD,
            headers=self.headers,
        )

    def assertNotFound(self, response, object_id, resource_name):
        self.assertEqual(response.json["errno"], 111)
        self.assertEqual(response.json["details"]["id"], object_id)
        self.assertEqual(response.json["details"]["resource_name"], resource_name)

    def test_invalid_bucket_id_returns_404_on_collections(self):
        resp = self.app.get("/buckets/*/collections", headers=self.headers, status=404)
        self.assertNotFound(resp, "*", "bucket")

    def test_invalid_bucket_id_returns_404_on_groups(self):
        resp = self.app.get("/buckets/*/groups", headers=self.headers, status=404)
        self.assertNotFound(resp, "*", "bucket")

    def test_invalid_bucket_id_returns_404_on_records(self):
        resp = self.app.get(
            "/buckets/*/collections/barley/records", headers=self.headers, status=404
        )
        self.assertNotFound(resp, "*", "bucket")

    def test_invalid_collection_id_returns_404_on_records(self):
        resp = self.app.get(
            "/buckets/beers/collections/*/records", headers=self.headers, status=404
        )
        self.assertNotFound(resp, "*", "collection")

    def test_invalid_bucket_id_returns_403_on_object_endpoints(self):
        self.app.get("/buckets/*/collections/barley", headers=self.headers, status=403)

    def test_partial_pattern_returns_404(self):
        resp = self.app.get("/buckets/be*/collections", headers=self.headers, status=404)
        self.assertNotFound(resp, "be*", "bucket")

    def test_percent_encoded_pattern_returns_404(self):
        resp = self.app.get("/buckets/%2A/collections", headers=self.headers, status=404)
        self.assertNotFound(resp, "*", "bucket")

    def test_creation_on_invalid_parent_returns_404(self):
        self.app.post_json(
            "/buckets/*/collections", MINIMALIST_COLLECTION, headers=self.headers, status=404
        )
        self.app.put_json(
            "/buckets/*/collections/barley",
            MINIMALIST_COLLECTION,
            headers=self.headers,
            status=404,
        )
