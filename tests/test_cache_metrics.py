# tests/test_cache_metrics.py

import unittest

from kinto.core.testing import (
    skip_if_no_memcached,
    skip_if_no_postgresql,
    skip_if_no_prometheus,
    skip_if_no_redis,
)

from .support import BaseWebTest


@skip_if_no_prometheus
class BaseCacheMetricsTest(BaseWebTest):
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

        # We should see 1 miss and 2 hits.
        self.assertIn("kinto_cache_misses_total 1.0", resp.text)
        self.assertIn("kinto_cache_hits_total 2.0", resp.text)


class MemoryCacheMetricsTest(BaseCacheMetricsTest, unittest.TestCase):
    """Run cache metrics tests with default (memory) backend."""

    pass


@skip_if_no_memcached
class MemcachedCacheMetricsTest(BaseCacheMetricsTest, unittest.TestCase):
    """Run cache metrics tests with Memcached cache backend."""

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        # Switch to Memcached backend
        settings["cache_backend"] = "kinto.core.cache.memcached"
        settings["cache_hosts"] = "127.0.0.1:11211"
        return settings


@skip_if_no_redis
class RedisCacheMetricsTest(BaseCacheMetricsTest, unittest.TestCase):
    """Run cache metrics tests with Redis cache backend."""

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["cache_backend"] = "kinto.core.cache.redis"
        return settings


@skip_if_no_postgresql
class PostgreSQLCacheMetricsTest(BaseCacheMetricsTest, unittest.TestCase):
    """Run cache metrics tests with PostgreSQL cache backend."""

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        # Switch to PostgreSQL backend
        settings["cache_backend"] = "kinto.core.cache.postgresql"
        settings["cache_url"] = "postgresql://postgres:postgres@localhost:5432/testdb"
        return settings
