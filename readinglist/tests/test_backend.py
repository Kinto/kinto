import six

import mock
import redis
import time

from readinglist.backend import BackendBase, exceptions
from readinglist.backend.simpleredis import (
    Redis, load_from_config as load_redis_from_config
)
from readinglist.backend.memory import Memory
from readinglist import utils

from .support import unittest, ThreadMixin


class BackendBaseTest(unittest.TestCase):
    def setUp(self):
        self.backend = BackendBase()

    def test_default_generator(self):
        self.assertEqual(type(self.backend.id_generator()), six.text_type)

    def test_custom_generator(self):
        l = lambda x: x
        backend = BackendBase(id_generator=l)
        self.assertEqual(backend.id_generator, l)

    def test_mandatory_overrides(self):
        calls = [
            (self.backend.flush,),
            (self.backend.ping,),
            (self.backend.last_collection_timestamp, '', ''),
            (self.backend.create, '', '', {}),
            (self.backend.get, '', '', ''),
            (self.backend.update, '', '', '', {}),
            (self.backend.delete, '', '', ''),
            (self.backend.get_all, '', ''),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class TestResource(object):
    id_field = "id"
    modified_field = "last_modified"


class BaseTestBackend(object):
    def setUp(self):
        super(BaseTestBackend, self).setUp()
        self.resource = TestResource()
        self.record = {'foo': 'bar'}
        self.user_id = 1234

    def tearDown(self):
        super(BaseTestBackend, self).tearDown()
        self.backend.flush()

    def test_create_adds_the_record_id(self):
        record = self.backend.create(self.resource, self.user_id, self.record)
        self.assertIsNotNone(record['id'])

    def test_create_works_as_expected(self):
        stored = self.backend.create(self.resource, self.user_id, self.record)
        retrieved = self.backend.get(self.resource, self.user_id, stored['id'])
        self.assertEquals(retrieved, stored)

    def test_create_copies_the_record_before_modifying_it(self):
        self.backend.create(self.resource, self.user_id, self.record)
        self.assertEquals(self.record.get('id'), None)

    def test_get_raise_on_record_not_found(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.backend.get,
            self.resource,
            self.user_id,
            1234  # This record id doesn't exist.
        )

    def test_update_creates_a_new_record_when_needed(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.backend.get,
            self.resource,
            self.user_id,
            1234  # This record id doesn't exist.
        )
        record = self.backend.update(self.resource, self.user_id, 1234,
                                     self.record)
        retrieved = self.backend.get(self.resource, self.user_id, 1234)
        self.assertEquals(retrieved, record)

    def test_update_overwrites_record_id(self):
        self.record['id'] = 4567
        self.backend.update(self.resource, self.user_id, 1234, self.record)
        retrieved = self.backend.get(self.resource, self.user_id, 1234)
        self.assertEquals(retrieved['id'], 1234)

    def test_delete_works_properly(self):
        stored = self.backend.create(self.resource, self.user_id, self.record)
        self.backend.delete(self.resource, self.user_id, stored['id'])
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.backend.get,
            self.resource, self.user_id, stored['id']  # Shouldn't exist.
        )

    def test_delete_raise_when_unknown(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.backend.delete,
            self.resource, self.user_id, 1234
        )

    def test_get_all_return_all_values(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x
            self.backend.create(self.resource, self.user_id, record)

        records = self.backend.get_all(self.resource, self.user_id)
        self.assertEquals(len(records), 10)

    def test_ping_returns_true_when_working(self):
        self.assertTrue(self.backend.ping())

    def test_timestamps_are_unique(self):
        obtained = []

        def create_item():
            for i in range(100):
                record = self.backend.create(
                    self.resource, self.user_id, self.record)
                obtained.append((record['last_modified'], record['id']))

        thread1 = self._create_thread(target=create_item)
        thread2 = self._create_thread(target=create_item)
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # With CPython (GIL), list appending is thread-safe
        self.assertEqual(len(obtained), 200)
        # No duplicated timestamps
        self.assertEqual(len(set(obtained)), len(obtained))

    def test_last_collection_timestamp_returns_now_when_not_found(self):
        before = utils.msec_time()
        time.sleep(0.001)  # 1 msec
        timestamp = self.backend.last_collection_timestamp(
            self.resource, self.user_id)
        time.sleep(0.001)  # 1 msec
        after = utils.msec_time()

        self.assertTrue(before < timestamp < after)


class RedisBackendTest(BaseTestBackend, ThreadMixin, unittest.TestCase):
    def setUp(self):
        super(RedisBackendTest, self).setUp()
        self.backend = Redis()

    def test_ping_returns_an_error_if_unavailable(self):
        self.backend._client.setex = mock.MagicMock(
            side_effect=redis.RedisError)
        self.assertFalse(self.backend.ping())

    def test_load_redis_from_config(self):
        class config:
            class registry:
                settings = {}

        load_redis_from_config(config)


class MemoryBackendTest(BaseTestBackend, ThreadMixin, unittest.TestCase):
    def setUp(self):
        super(MemoryBackendTest, self).setUp()
        self.backend = Memory()

    def test_ping_returns_an_error_if_unavailable(self):
        pass
