import time
import unittest
from unittest import mock

from kinto.core.cache import CacheBase
from kinto.core.cache import memcached as memcached_backend
from kinto.core.cache import memory as memory_backend
from kinto.core.cache import postgresql as postgresql_backend
from kinto.core.cache.testing import CacheTest
from kinto.core.testing import skip_if_no_memcached, skip_if_no_postgresql
from kinto.core.utils import memcache, sqlalchemy


class CacheBaseTest(unittest.TestCase):
    def setUp(self):
        self.cache = CacheBase(cache_prefix="")

    def test_mandatory_overrides(self):
        calls = [
            (self.cache.initialize_schema,),
            (self.cache.flush,),
            (self.cache.ttl, ""),
            (self.cache.expire, "", ""),
            (self.cache.get, ""),
            (self.cache.set, "", "", 42),
            (self.cache.delete, ""),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class MemoryCacheTest(CacheTest, unittest.TestCase):
    backend = memory_backend
    settings = {"cache_prefix": "", "cache_max_size_bytes": 7000}

    def get_backend_prefix(self, prefix):
        backend_prefix = CacheTest.get_backend_prefix(self, prefix)

        # Share the store between both client for tests.
        backend_prefix._ttl = self.cache._ttl
        backend_prefix._store = self.cache._store

        return backend_prefix

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass

    def test_ping_logs_error_if_unavailable(self):
        pass

    def test_clean_expired_expires_items(self):
        self.cache.set("foobar", "toto", 0.01)
        assert "foobar" in self.cache._store
        assert "foobar" in self.cache._ttl
        assert "foobar" in self.cache._created_at
        time.sleep(0.02)
        retrieved = self.cache._clean_expired()
        assert "foobar" not in self.cache._store
        assert "foobar" not in self.cache._ttl
        assert "foobar" not in self.cache._created_at
        self.assertIsNone(retrieved)

    def test_add_over_quota_clean_oversized_items(self):
        for x in range(100):
            # Each entry is 70 bytes
            self.cache.set("foo{0:03d}".format(x), "toto", 42)
            time.sleep(0.001)
        assert self.cache.get("foo000") == "toto"
        # This should delete the 2 first entries
        self.cache.set("foobar", "tata", 42)
        assert self.cache._quota == 7000 - 70 * 20
        assert self.cache.get("foo000") is None
        assert self.cache.get("foobar") == "tata"

    def test_size_quota_can_be_set_to_zero(self):
        before = self.cache.max_size_bytes
        self.cache.max_size_bytes = 0
        self.cache.set("foobar", "tata", 42)
        self.cache.max_size_bytes = before
        assert self.cache.get("foobar") == "tata"


@skip_if_no_memcached
class MemcachedCacheTest(CacheTest, unittest.TestCase):
    backend = memcached_backend
    settings = {"cache_prefix": "", "cache_hosts": "127.0.0.1:11211"}

    def setUp(self):
        super().setUp()
        self.client_error_patcher = mock.patch.object(
            self.cache._client.servers[0], "connect", side_effect=memcache.Client.MemcachedKeyError
        )

    def test_set_with_ttl_expires_the_value(self):
        self.cache.set("foobar", "toto", 1)
        time.sleep(1.1)
        retrieved = self.cache.get("foobar")
        self.assertIsNone(retrieved)

    def test_expire_expires_the_value(self):
        self.cache.set("foobar", "toto", 42)
        self.cache.expire("foobar", 1)
        time.sleep(1.1)
        retrieved = self.cache.get("foobar")
        self.assertIsNone(retrieved)


@skip_if_no_postgresql
class PostgreSQLCacheTest(CacheTest, unittest.TestCase):
    backend = postgresql_backend
    settings = {
        "cache_backend": "kinto.core.cache.postgresql",
        "cache_pool_size": 10,
        "cache_url": "postgresql://postgres:postgres@localhost:5432/testdb",
        "cache_prefix": "",
    }

    def setUp(self):
        super().setUp()
        self.client_error_patcher = mock.patch.object(
            self.cache.client, "session_factory", side_effect=sqlalchemy.exc.SQLAlchemyError
        )
