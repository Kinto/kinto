# tests/test_cache_metrics.py

import unittest

from kinto.core.testing import skip_if_no_prometheus

from .support import BaseWebTest


@skip_if_no_prometheus
class CacheMetricsTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] += "\nkinto.plugins.prometheus"
        return settings

    def setUp(self):
        super().setUp()
        from kinto.plugins.prometheus import reset_registry

        reset_registry()

    def test_cache_miss_and_hit_counters(self):
        # Miss: key does not exist.
        self.cache.get("unknown-key")

        # Hits: store then retrieve twice.
        self.cache.set("foo", {"bar": 42}, ttl=30)
        self.cache.get("foo")
        self.cache.get("foo")

        # Fetch the raw Prometheus metrics.
        resp = self.app.get("/__metrics__")

        # We should see exactly 1 miss and 1 hit.
        self.assertIn("kinto_cache_misses_total 1.0", resp.text)
        self.assertIn("kinto_cache_hits_total 2.0", resp.text)
