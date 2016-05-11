import mock
import time

import redis
from pyramid import testing

from cliquet.utils import sqlalchemy
from cliquet.storage import exceptions
from cliquet.cache import (CacheBase, postgresql as postgresql_backend,
                           redis as redis_backend, memory as memory_backend,
                           heartbeat)

from .support import unittest, skip_if_no_postgresql


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


class BaseTestCache(object):
    backend = None
    settings = {}

    def setUp(self):
        super(BaseTestCache, self).setUp()
        self.cache = self.backend.load_from_config(self._get_config())
        self.cache.initialize_schema()
        self.request = None
        self.client_error_patcher = None

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        config = testing.setUp()
        config.add_settings(settings)
        return config

    def tearDown(self):
        mock.patch.stopall()
        super(BaseTestCache, self).tearDown()
        self.cache.flush()

    def get_backend_prefix(self, prefix):
        settings_prefix = self.settings.copy()
        settings_prefix['cache_prefix'] = prefix
        config_prefix = self._get_config(settings=settings_prefix)

        # initiating cache backend with prefix:
        backend_prefix = self.backend.load_from_config(config_prefix)

        return backend_prefix

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
        ping = heartbeat(self.cache)
        self.assertFalse(ping(self.request))
        with mock.patch('cliquet.cache.random.random', return_value=0.6):
            self.assertFalse(ping(self.request))
        with mock.patch('cliquet.cache.random.random', return_value=0.4):
            self.assertFalse(ping(self.request))

    def test_ping_returns_true_if_available(self):
        ping = heartbeat(self.cache)
        with mock.patch('cliquet.cache.random.random', return_value=0.6):
            self.assertTrue(ping(self.request))
        with mock.patch('cliquet.cache.random.random', return_value=0.4):
            self.assertTrue(ping(self.request))

    def test_ping_logs_error_if_unavailable(self):
        self.client_error_patcher.start()
        ping = heartbeat(self.cache)

        with mock.patch('cliquet.cache.logger.exception') as exc_handler:
            self.assertFalse(ping(self.request))

        self.assertTrue(exc_handler.called)

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

    def test_cache_prefix_is_set(self):
        backend_prefix = self.get_backend_prefix(prefix='prefix_')

        # Set the value
        backend_prefix.set('key', 'foo')

        # Validate that it was set with the prefix.
        obtained = self.cache.get('prefix_key')
        self.assertEqual(obtained, 'foo')

    def test_cache_when_prefix_is_not_set(self):
        backend_prefix = self.get_backend_prefix(prefix='')

        # Set a value
        backend_prefix.set('key', 'foo')

        # Validate that it was set with no prefix
        obtained = self.cache.get('key')
        self.assertEqual(obtained, 'foo')

    def test_prefix_value_use_to_get_data(self):
        backend_prefix = self.get_backend_prefix(prefix='prefix_')

        # Set the value with the prefix
        self.cache.set('prefix_key', 'foo')

        # Validate that the prefix was added
        obtained = backend_prefix.get('key')
        self.assertEqual(obtained, 'foo')

    def test_prefix_value_use_to_delete_data(self):
        backend_prefix = self.get_backend_prefix(prefix='prefix_')
        # Set the value
        self.cache.set('prefix_key', 'foo')

        # Delete the value
        backend_prefix.delete('key')

        # Validate that the value was deleted
        obtained = self.cache.get('prefix_key')
        self.assertEqual(obtained, None)

    def test_prefix_value_used_with_ttl(self):
        backend_prefix = self.get_backend_prefix(prefix='prefix_')

        self.cache.set('prefix_key', 'foo', 10)

        # Validate that the ttl add the prefix to the key.
        obtained = backend_prefix.ttl('key')
        self.assertLessEqual(obtained, 10)
        self.assertGreater(obtained, 9)

    def test_prefix_value_used_with_expire(self):
        backend_prefix = self.get_backend_prefix(prefix='prefix_')

        self.cache.set('prefix_foobar', 'toto', 10)

        # expiring the ttl of key
        backend_prefix.expire('foobar', 0)

        # Make sure the TTL was set accordingly.
        ttl = self.cache.ttl('prefix_foobar')
        self.assertLessEqual(ttl, 0)

        # The record should have expired
        retrieved = self.cache.get('prefix_foobar')
        self.assertIsNone(retrieved)


class MemoryCacheTest(BaseTestCache, unittest.TestCase):
    backend = memory_backend
    settings = {
        'cache_prefix': ''
    }

    def get_backend_prefix(self, prefix):
        backend_prefix = BaseTestCache.get_backend_prefix(self, prefix)

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


class RedisCacheTest(BaseTestCache, unittest.TestCase):
    backend = redis_backend
    settings = {
        'cache_url': '',
        'cache_pool_size': 10,
        'cache_prefix': ''
    }

    def setUp(self):
        super(RedisCacheTest, self).setUp()
        self.client_error_patcher = mock.patch.object(
            self.cache._client,
            'execute_command',
            side_effect=redis.RedisError)

    def test_config_is_taken_in_account(self):
        config = testing.setUp(settings=self.settings)
        config.add_settings({'cache_url': 'redis://:secret@peer.loc:4444/7'})
        backend = self.backend.load_from_config(config)
        self.assertDictEqual(
            backend.settings,
            {'host': 'peer.loc', 'password': 'secret', 'db': 7, 'port': 4444})


@skip_if_no_postgresql
class PostgreSQLCacheTest(BaseTestCache, unittest.TestCase):
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
