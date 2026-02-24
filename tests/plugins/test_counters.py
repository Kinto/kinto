import unittest

from ..support import MINIMALIST_BUCKET, MINIMALIST_COLLECTION, MINIMALIST_RECORD, BaseWebTest


class CountersViewTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super().setUp()

        for bid in ("a", "b", "c", "d"):
            self.app.put_json(f"/buckets/{bid}", MINIMALIST_BUCKET, headers=self.headers)
            for cid in ("e", "f", "g"):
                self.app.put_json(
                    f"/buckets/{bid}/collections/{cid}",
                    MINIMALIST_COLLECTION,
                    headers=self.headers,
                )
                for i in range(3):
                    resp = self.app.post_json(
                        f"/buckets/{bid}/collections/{cid}/records",
                        MINIMALIST_RECORD,
                        headers=self.headers,
                    )
                    if i % 2 != 0:
                        resp = self.app.delete(
                            f"/buckets/{bid}/collections/{cid}/records/{resp.json['data']['id']}",
                            headers=self.headers,
                        )

    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {}
        extras.setdefault("includes", "kinto.plugins.counters kinto.plugins.history")
        settings = super().get_app_settings(extras)
        return settings

    def test_returns_404_if_not_enabled_in_configuration(self):
        app = self.make_app(settings={"includes": ""})
        app.get("/__counters__", headers=self.headers, status=404)

    def test_flush_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("counters_endpoint", capabilities)

    def test_counts_all_kinds_of_objects(self):
        resp = self.app.get("/__counters__", headers=self.headers)
        counters = resp.json
        assert counters == {
            "objects": {
                "bucket": 4,
                "collection": 12,
                "record": 24,
                "history": 64,
            },
            "tombstones": {
                "record": 12,
            },
        }
