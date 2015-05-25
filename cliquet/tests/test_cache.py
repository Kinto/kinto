import mock
import time

import psycopg2
import redis

from cliquet.storage import exceptions
from cliquet.cache import (CacheBase, postgresql as postgresql_backend,
                           redis as redis_backend, memory as memory_backend)

from .support import unittest


class CacheBaseTest(unittest.TestCase):
    def setUp(self):
        self.cache = CacheBase()

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


class BaseTestCache(object):
    backend = None
    settings = {}

    def __init__(self, *args, **kwargs):
        super(BaseTestCache, self).__init__(*args, **kwargs)
        self.cache = self.backend.load_from_config(self._get_config())
        self.cache.initialize_schema()
        self.request = None
        self.client_error_patcher = None

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        return mock.Mock(get_settings=mock.Mock(return_value=settings))

    def tearDown(self):
        mock.patch.stopall()
        super(BaseTestCache, self).tearDown()
        self.cache.flush()

    def test_backend_error_is_raised_anywhere(self):
        self.client_error_patcher.start()
        calls = [
            (self.cache.flush,),
            (self.cache.ttl, ''),
            (self.cache.expire, '', 0),
            (self.cache.get, ''),
            (self.cache.set, '', ''),
            (self.cache.delete, ''),
        ]
        for call in calls:
            self.assertRaises(exceptions.BackendError, *call)

    def test_ping_returns_false_if_unavailable(self):
        self.client_error_patcher.start()
        self.assertFalse(self.cache.ping(self.request))
        with mock.patch('cliquet.cache.random.random', return_value=0.6):
            self.assertFalse(self.cache.ping(self.request))
        with mock.patch('cliquet.cache.random.random', return_value=0.4):
            self.assertFalse(self.cache.ping(self.request))

    def test_ping_returns_true_if_available(self):
        with mock.patch('cliquet.cache.random.random', return_value=0.6):
            self.assertTrue(self.cache.ping(self.request))
        with mock.patch('cliquet.cache.random.random', return_value=0.4):
            self.assertTrue(self.cache.ping(self.request))

    def test_set_adds_the_record(self):
        stored = 'toto'
        self.cache.set('foobar', stored)
        retrieved = self.cache.get('foobar')
        self.assertEquals(retrieved, stored)

    def test_values_remains_python_dict(self):
        def setget(k, v):
            self.cache.set(k, v)
            return (self.cache.get(k), v)

        self.assertEqual(*setget('foobar', 3))
        self.assertEqual(*setget('foobar', ['a']))
        self.assertEqual(*setget('foobar', {'b': [1, 2]}))
        self.assertEqual(*setget('foobar', 3.14))

    def test_delete_removes_the_record(self):
        self.cache.set('foobar', 'toto')
        self.cache.delete('foobar')
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)

    def test_delete_does_not_fail_if_record_is_unknown(self):
        self.cache.delete('foobar')

    def test_expire_expires_the_value(self):
        self.cache.set('foobar', 'toto')
        self.cache.expire('foobar', 0.01)
        time.sleep(0.02)
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)

    def test_set_with_ttl_expires_the_value(self):
        self.cache.set('foobar', 'toto', 0.01)
        time.sleep(0.02)
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)

    def test_ttl_return_the_time_to_live(self):
        self.cache.set('foobar', 'toto')
        self.cache.expire('foobar', 10)
        ttl = self.cache.ttl('foobar')
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)

    def test_ttl_return_none_if_unknown(self):
        ttl = self.cache.ttl('unknown')
        self.assertTrue(ttl < 0)


class MemoryCacheTest(BaseTestCache, unittest.TestCase):
    backend = memory_backend

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass


class RedisCacheTest(BaseTestCache, unittest.TestCase):
    backend = redis_backend
    settings = {
        'cliquet.cache_url': '',
        'cliquet.cache_pool_size': 10
    }

    def __init__(self, *args, **kwargs):
        super(RedisCacheTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.cache._client,
            'execute_command',
            side_effect=redis.RedisError)


class PostgreSQLCacheTest(BaseTestCache, unittest.TestCase):
    backend = postgresql_backend
    settings = {
        'cliquet.cache_pool_size': 10,
        'cliquet.cache_url':
            'postgres://postgres:postgres@localhost:5432/testdb'
    }

    def __init__(self, *args, **kwargs):
        super(PostgreSQLCacheTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.cache.pool,
            'getconn',
            side_effect=psycopg2.DatabaseError)
