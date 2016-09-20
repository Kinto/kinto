import mock
import unittest

from kinto.core.utils import sqlalchemy
from kinto.core.cache import (CacheBase, memory as memory_backend,
                              postgresql as postgresql_backend)

from kinto.core.testing import skip_if_no_postgresql
from kinto.core.cache.testing import CacheTest


class CacheBaseTest(unittest.TestCase):
    def setUp(self):
        self.cache = CacheBase(cache_prefix='')

    def test_mandatory_overrides(self):
        calls = [
            (self.cache.initialize_schema,),
            (self.cache.flush,),
            (self.cache.ttl, ''),
            (self.cache.expire, '', ''),
            (self.cache.get, ''),
            (self.cache.set, '', ''),
            (self.cache.delete, ''),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class MemoryCacheTest(CacheTest, unittest.TestCase):
    backend = memory_backend
    settings = {
        'cache_prefix': ''
    }

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


@skip_if_no_postgresql
class PostgreSQLCacheTest(CacheTest, unittest.TestCase):
    backend = postgresql_backend
    settings = {
        'cache_pool_size': 10,
        'cache_url': 'postgres://postgres:postgres@localhost:5432/testdb',
        'cache_prefix': ''
    }

    def setUp(self):
        super(PostgreSQLCacheTest, self).setUp()
        self.client_error_patcher = mock.patch.object(
            self.cache.client,
            'session_factory',
            side_effect=sqlalchemy.exc.SQLAlchemyError)
