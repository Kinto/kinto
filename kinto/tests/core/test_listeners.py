# -*- coding: utf-8 -*-
import json
import uuid
from contextlib import contextmanager
from datetime import datetime

import mock
from pyramid import testing

from kinto.core import initialization
from kinto.core.events import ResourceChanged, ResourceRead, ACTIONS
from kinto.core.listeners import ListenerBase
from kinto.core.storage.redis import create_from_config
from kinto.tests.core.support import unittest


class ListenerSetupTest(unittest.TestCase):
    def setUp(self):
        redis_patch = mock.patch('kinto.core.listeners.redis.load_from_config')
        self.addCleanup(redis_patch.stop)
        self.redis_mocked = redis_patch.start()

    def make_app(self, extra_settings={}):
        settings = {
            'event_listeners': 'kinto.core.listeners.redis',
        }
        settings.update(**extra_settings)
        config = testing.setUp(settings=settings)
        config.commit()
        initialization.setup_listeners(config)
        return config

    def test_listener_module_is_specified_via_settings(self):
        self.make_app({
            'event_listeners': 'redis',
            'event_listeners.redis.use': 'kinto.core.listeners.redis',
        })
        self.assertTrue(self.redis_mocked.called)

    def test_listener_module_can_be_specified_via_listeners_list(self):
        self.make_app()
        self.assertTrue(self.redis_mocked.called)

    def test_callback_called_when_action_is_not_filtered(self):
        config = self.make_app()
        event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
        config.registry.notify(event)

        self.assertTrue(self.redis_mocked.return_value.called)

    def test_callback_is_not_called_when_action_is_filtered(self):
        config = self.make_app({
            'event_listeners.redis.actions': 'delete',
        })
        event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
        config.registry.notify(event)

        self.assertFalse(self.redis_mocked.return_value.called)

    def test_callback_called_when_resource_is_not_filtered(self):
        config = self.make_app()
        event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
        event.payload['resource_name'] = 'mushroom'
        config.registry.notify(event)

        self.assertTrue(self.redis_mocked.return_value.called)

    def test_callback_is_not_called_when_resource_is_filtered(self):
        config = self.make_app({
            'event_listeners.redis.resources': 'toad',
        })
        event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
        event.payload['resource_name'] = 'mushroom'
        config.registry.notify(event)

        self.assertFalse(self.redis_mocked.return_value.called)

    def test_callback_is_not_called_on_read_by_default(self):
        config = self.make_app()
        event = ResourceRead(ACTIONS.READ, 123456, [], Request())
        config.registry.notify(event)

        self.assertFalse(self.redis_mocked.return_value.called)

    def test_callback_is_called_on_read_if_specified(self):
        config = self.make_app({
            'event_listeners.redis.actions': 'read',
        })
        event = ResourceRead(ACTIONS.READ, 123456, [], Request())
        config.registry.notify(event)

        self.assertTrue(self.redis_mocked.return_value.called)

    def test_same_callback_is_called_for_read_and_write_specified(self):
        config = self.make_app({
            'event_listeners.redis.actions': 'read create delete',
        })
        event = ResourceRead(ACTIONS.READ, 123456, [], Request())
        config.registry.notify(event)
        event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
        config.registry.notify(event)

        self.assertEqual(self.redis_mocked.return_value.call_count, 2)


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
    current_resource_name = 'bucket'


class ListenerCalledTest(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.add_settings({'events_pool_size': 1,
                                  'events_url': 'redis://localhost:6379/0'})
        self._redis = create_from_config(self.config, prefix='events_')
        self._size = 0

    def _save_redis(self):
        self._size = self._redis.llen('kinto.core.events')

    def has_redis_changed(self):
        return self._redis.llen('kinto.core.events') > self._size

    def notify(self, event):
        self._save_redis()
        self.config.registry.notify(event)

    @contextmanager
    def redis_listening(self):
        config = self.config
        listener = 'kinto.core.listeners.redis'

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
            event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
            self.notify(event)
            self.assertTrue(self.has_redis_changed())

        # okay, we should have the first event in Redis
        last = self._redis.lpop('kinto.core.events')
        last = json.loads(last.decode('utf8'))
        self.assertEqual(last['action'], ACTIONS.CREATE.value)

    def test_notification_is_broken(self):
        with self.redis_listening():
            # an event with a bad JSON should silently break and send nothing
            # date time objects cannot be dumped
            event2 = ResourceChanged(ACTIONS.CREATE,
                                     datetime.now(),
                                     [],
                                     Request())
            self.notify(event2)
            self.assertFalse(self.has_redis_changed())

    def test_redis_is_broken(self):
        with self.redis_listening():
            # if the redis call fails, same deal: we should ignore it
            self._save_redis()

            with broken_redis():
                event = ResourceChanged(ACTIONS.CREATE, 123456, [], Request())
                self.config.registry.notify(event)

            self.assertFalse(self.has_redis_changed())


class ListenerBaseTest(unittest.TestCase):

    def test_not_implemented(self):
        # make sure we can't use the base listener
        listener = ListenerBase()
        self.assertRaises(NotImplementedError, listener, object())
