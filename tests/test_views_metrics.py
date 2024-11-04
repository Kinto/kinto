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

        resp = self.app.get("/__metrics__")
        self.assertIn(
            'request_size_sum{bucket_id="beers",collection_id="",endpoint="/buckets/beers",group_id="",record_id=""}',
            resp.text,
        )
        self.assertIn(
            'request_size_sum{bucket_id="beers",collection_id="",endpoint="/buckets/beers/groups/amateurs",group_id="amateurs",record_id=""}',
            resp.text,
        )
        self.assertIn(
            'request_summary_total{bucket_id="beers",collection_id="barley",endpoint="/buckets/beers/collections/barley",group_id="",method="put",record_id="",status="201"}',
            resp.text,
        )
        self.assertIn(
            'request_duration_sum{bucket_id="beers",collection_id="barley",endpoint="/buckets/beers/collections/barley/records/abc",group_id="",record_id="abc"}',
            resp.text,
        )
