import unittest
from unittest import mock

from kinto.core.testing import skip_if_no_prometheus

from .support import BaseWebTest


@skip_if_no_prometheus
class ViewsMetricsTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] += "\nkinto.plugins.prometheus"
        return settings

    def setUp(self):
        super().setUp()
        patch = mock.patch("kinto.plugins.prometheus.PrometheusService")
        self.mocked = patch.start()
        self.addCleanup(patch.stop)

    def test_metrics_have_matchdict_labels(self):
        self.app.put("/buckets/beers", headers=self.headers)
        self.app.put("/buckets/beers/groups/amateurs", headers=self.headers)
        self.app.put("/buckets/beers/collections/barley", headers=self.headers)
        self.app.put("/buckets/beers/collections/barley/records/abc", headers=self.headers)

        self.app.get("/buckets", headers=self.headers)
        self.app.get("/buckets/beers/collections", headers=self.headers)
        self.app.get("/buckets/beers/collections/barley/records", headers=self.headers)

        resp = self.app.get("/__metrics__")

        self.assertIn(
            'request_size_sum{bucket_id="beers",collection_id="",endpoint="bucket-object",group_id="",method="put",record_id=""}',
            resp.text,
        )
        self.assertIn(
            'request_size_sum{bucket_id="beers",collection_id="",endpoint="group-object",group_id="amateurs",method="put",record_id=""}',
            resp.text,
        )
        self.assertIn(
            'request_duration_seconds_sum{bucket_id="beers",collection_id="barley",endpoint="record-object",group_id="",method="put",record_id="abc"}',
            resp.text,
        )
        self.assertIn(
            'request_summary_total{bucket_id="beers",collection_id="barley",endpoint="collection-object",group_id="",method="put",record_id="",status="201"}',
            resp.text,
        )
        self.assertIn(
            'request_summary_total{bucket_id="",collection_id="",endpoint="bucket-plural",group_id="",method="get",record_id="",status="200"}',
            resp.text,
        )
        self.assertIn(
            'request_summary_total{bucket_id="beers",collection_id="",endpoint="collection-plural",group_id="",method="get",record_id="",status="200"}',
            resp.text,
        )
        self.assertIn(
            'request_summary_total{bucket_id="beers",collection_id="barley",endpoint="record-plural",group_id="",method="get",record_id="",status="200"}',
            resp.text,
        )

    def test_4xx_do_not_have_matchdict_labels_values(self):
        self.app.get("/buckets/water", headers=self.headers, status=403)

        resp = self.app.get("/__metrics__")

        self.assertIn(
            'request_summary_total{bucket_id="",collection_id="",endpoint="bucket-object",group_id="",method="get",record_id="",status="403"}',
            resp.text,
        )
