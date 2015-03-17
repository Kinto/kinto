import mock
import time

import psycopg2
import redis

from cliquet.storage import exceptions
from cliquet.session import SessionStorageBase, SessionCache
from cliquet.session import (postgresql as postgresql_backend,
                             redis as redis_backend)

from .support import unittest


class SessionStorageBaseTest(unittest.TestCase):
    def setUp(self):
        self.session = SessionStorageBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.session.flush,),
            (self.session.ping,),
            (self.session.ttl, ''),
            (self.session.expire, '', ''),
            (self.session.get, ''),
            (self.session.set, '', ''),
            (self.session.delete, ''),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class BaseTestSessionStorage(object):
    backend = None

    settings = {
        'cliquet.session_url': ''
    }

    def __init__(self, *args, **kwargs):
        super(BaseTestSessionStorage, self).__init__(*args, **kwargs)
        self.session = self.backend.load_from_config(self._get_config())
        self.client_error_patcher = None

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        return mock.Mock(registry=mock.Mock(settings=settings))

    def tearDown(self):
        mock.patch.stopall()
        super(BaseTestSessionStorage, self).tearDown()
        self.session.flush()

    def test_backend_error_is_raised_anywhere(self):
        self.client_error_patcher.start()
        calls = [
            (self.session.flush,),
            (self.session.ttl, ''),
            (self.session.expire, '', 0),
            (self.session.get, ''),
            (self.session.set, '', ''),
            (self.session.delete, ''),
        ]
        for call in calls:
            self.assertRaises(exceptions.BackendError, *call)

    def test_ping_returns_an_error_if_unavailable(self):
        self.client_error_patcher.start()
        self.assertFalse(self.session.ping())

    def test_ping_returns_true_if_available(self):
        self.assertTrue(self.session.ping())

    def test_set_adds_the_record(self):
        stored = 'toto'
        self.session.set('foobar', stored)
        retrieved = self.session.get('foobar')
        self.assertEquals(retrieved, stored)

    def test_delete_removes_the_record(self):
        self.session.set('foobar', 'toto')
        self.session.delete('foobar')
        retrieved = self.session.get('foobar')
        self.assertIsNone(retrieved)

    def test_expire_expires_the_value(self):
        self.session.set('foobar', 'toto')
        self.session.expire('foobar', 0.05)
        time.sleep(0.1)
        retrieved = self.session.get('foobar')
        self.assertIsNone(retrieved)

    def test_set_with_ttl_expires_the_value(self):
        self.session.set('foobar', 'toto', 0.05)
        time.sleep(0.1)
        retrieved = self.session.get('foobar')
        self.assertIsNone(retrieved)

    def test_ttl_return_the_time_to_live(self):
        self.session.set('foobar', 'toto')
        self.session.expire('foobar', 10)
        ttl = self.session.ttl('foobar')
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)


class RedisSessionStorageTest(BaseTestSessionStorage, unittest.TestCase):
    backend = redis_backend

    def __init__(self, *args, **kwargs):
        super(RedisSessionStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.session._client,
            'execute_command',
            side_effect=redis.RedisError)


class PostgreSQLSessionStorageTest(BaseTestSessionStorage, unittest.TestCase):
    backend = postgresql_backend

    settings = {
        'cliquet.session_url':
            'postgres://postgres:postgres@localhost:5432/testdb'
    }

    def __init__(self, *args, **kwargs):
        super(PostgreSQLSessionStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch(
            'cliquet.storage.postgresql.psycopg2.connect',
            side_effect=psycopg2.OperationalError)


class SessionCacheTest(unittest.TestCase):
    def setUp(self):
        self.cache = SessionCache(redis_backend.Redis(), 0.05)
        super(SessionCacheTest, self).setUp()

    def test_set_adds_the_record(self):
        stored = 'toto'
        self.cache.set('foobar', stored)
        retrieved = self.cache.get('foobar')
        self.assertEquals(retrieved, stored)

    def test_delete_removes_the_record(self):
        self.cache.set('foobar', 'toto')
        self.cache.delete('foobar')
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)

    def test_set_expires_the_value(self):
        self.cache.set('foobar', 'toto')
        time.sleep(0.1)
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)
