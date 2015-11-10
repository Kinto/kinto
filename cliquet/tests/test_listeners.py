# -*- coding: utf-8 -*-
import mock
from pyramid import testing
import uuid
import redis
import json
from datetime import datetime
from contextlib import contextmanager

from cliquet import initialization
from cliquet.events import ResourceChanged, ACTIONS
from cliquet.listeners import ListenerBase
from .support import unittest


class ListenerSetupTest(unittest.TestCase):
    def test_redis_listener_is_enabled_via_setting(self):
        listener = 'cliquet.listeners.redis'
        redis_class = mock.patch(listener + '.RedisListener')
        config = testing.setUp()
        with mock.patch.dict(config.registry.settings,
                             [('event_listeners', listener)]):
            with redis_class as redis_mocked:
                initialization.setup_listeners(config)
                self.assertTrue(redis_mocked.called)


@contextmanager
def broken_redis():
    from redis import StrictRedis
    old = StrictRedis.lpush

    def push(*args, **kwargs):
        raise Exception('boom')

    StrictRedis.lpush = push
    yield
    StrictRedis.lpush = old

UID = str(uuid.uuid4())


class Resource(object):
    record_id = UID
    timestamp = 123456789


class ViewSet(object):
    def get_name(*args, **kw):
        return 'collection'


class Service(object):
    viewset = ViewSet()


class Match(object):
    cornice_services = {'watev': Service()}
    pattern = 'watev'


class Request(object):
    path = '/1/bucket/collection/'
    prefixed_userid = 'tarek'
    matchdict = {'id': UID}
    registry = matched_route = Match()


class ListenerCalledTest(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        pool = redis.BlockingConnectionPool(max_connections=1,
                                            host='localhost', port=6379, db=0)
        self._redis = redis.StrictRedis(connection_pool=pool)
        self._size = 0

    def _save_redis(self):
        self._size = self._redis.llen('cliquet.events')

    def has_redis_changed(self):
        return self._redis.llen('cliquet.events') > self._size

    def notify(self, event):
        self._save_redis()
        self.config.registry.notify(event)

    @contextmanager
    def redis_listening(self):
        config = self.config
        listener = 'cliquet.listeners.redis'

        # setting up the redis listener
        with mock.patch.dict(config.registry.settings,
                             [('event_listeners', listener),
                              ('event_listeners.redis.pool_size', '1')]):
            initialization.setup_listeners(config)
            config.commit()
            yield

    def test_redis_is_notified(self):
        with self.redis_listening():
            # let's trigger an event
            event = ResourceChanged('create', Resource(), Request())
            self.notify(event)
            self.assertTrue(self.has_redis_changed())

        # okay, we should have the first event in Redis
        last = self._redis.lpop('cliquet.events')
        last = json.loads(last.decode('utf8'))
        self.assertEqual(last['action'], ACTIONS.CREATE)

    def test_notification_is_broken(self):
        with self.redis_listening():
            # an event with a bad JSON should silently break and send nothing
            res = Resource()
            # date time objects cannot be dumped
            res.timestamp = datetime.now()
            event2 = ResourceChanged('create', res, Request())
            self.notify(event2)
            self.assertFalse(self.has_redis_changed())

    def test_redis_is_broken(self):
        with self.redis_listening():
            # if the redis call fails, same deal: we should ignore it
            self._save_redis()

            with broken_redis():
                event = ResourceChanged('create', Resource(), Request())
                self.config.registry.notify(event)

            self.assertFalse(self.has_redis_changed())


class ListenerBaseTest(unittest.TestCase):

    def test_not_implemented(self):
        # make sure we can't use the base listener
        listener = ListenerBase()
        self.assertRaises(NotImplementedError, listener, object())
