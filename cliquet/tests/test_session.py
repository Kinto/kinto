import mock
import redis
import time

from cliquet.session import SessionStorageBase, SessionCache
from cliquet.session.redis import (
    RedisSessionStorage, load_from_config as load_redis_from_config
)

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
    def setUp(self):
        super(BaseTestSessionStorage, self).setUp()

    def tearDown(self):
        super(BaseTestSessionStorage, self).tearDown()
        self.session.flush()

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
    def setUp(self):
        self.session = RedisSessionStorage()
        super(RedisSessionStorageTest, self).setUp()

    def test_ping_returns_true_if_available(self):
        self.assertTrue(self.session.ping())

    def test_ping_returns_an_error_if_unavailable(self):
        self.session._client.setex = mock.MagicMock(
            side_effect=redis.RedisError)
        self.assertFalse(self.session.ping())

    def test_load_redis_from_config(self):
        class config:
            class registry:
                settings = {}

        load_redis_from_config(config)


class SessionCacheTest(unittest.TestCase):
    def setUp(self):
        self.cache = SessionCache(RedisSessionStorage(), 0.05)
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
