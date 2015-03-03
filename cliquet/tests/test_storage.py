import mock
import redis
import six
import time

import psycopg2
from cliquet.storage import (
    exceptions, Filter, memory,
    redis as redisbackend, postgresql,
    Sort, StorageBase
)
from cliquet import utils
from cliquet import schema
from pyramid import httpexceptions
from pyramid.config import global_registries

from .support import unittest, ThreadMixin


class StorageBaseTest(unittest.TestCase):
    def setUp(self):
        self.storage = StorageBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.storage.flush,),
            (self.storage.ping,),
            (self.storage.collection_timestamp, '', ''),
            (self.storage.create, '', '', {}),
            (self.storage.get, '', '', ''),
            (self.storage.update, '', '', '', {}),
            (self.storage.delete, '', '', ''),
            (self.storage.delete_all, '', ''),
            (self.storage.get_all, '', ''),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)


class TestMapping(schema.ResourceSchema):
    class Options:
        pass


class TestResource(object):
    id_field = "id"
    name = "test"
    modified_field = "last_modified"
    mapping = TestMapping()
    deleted_field = "deleted"


class BaseTestStorage(object):
    backend = None

    settings = {}

    def __init__(self, *args, **kwargs):
        super(BaseTestStorage, self).__init__(*args, **kwargs)
        self.storage = self.backend.load_from_config(self._get_config())
        self.resource = TestResource()
        self.user_id = '1234'
        self.record = {'foo': 'bar'}

    def _get_config(self):
        """Mock Pyramid config object.
        """
        return mock.Mock(registry=mock.Mock(settings=self.settings))

    def tearDown(self):
        super(BaseTestStorage, self).tearDown()
        self.storage.flush()
        self.resource.mapping = TestMapping()

    def test_ping_returns_true_when_working(self):
        self.assertTrue(self.storage.ping())

    def test_create_adds_the_record_id(self):
        record = self.storage.create(self.resource, self.user_id, self.record)
        self.assertIsNotNone(record['id'])

    def test_create_works_as_expected(self):
        stored = self.storage.create(self.resource, self.user_id, self.record)
        retrieved = self.storage.get(self.resource, self.user_id, stored['id'])
        self.assertEquals(retrieved, stored)

    def test_create_copies_the_record_before_modifying_it(self):
        self.storage.create(self.resource, self.user_id, self.record)
        self.assertEquals(self.record.get('id'), None)

    def test_get_raise_on_record_not_found(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            self.resource,
            self.user_id,
            '1234'  # This record id doesn't exist.
        )

    def test_update_creates_a_new_record_when_needed(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            self.resource,
            self.user_id,
            '1234'  # This record id doesn't exist.
        )
        record = self.storage.update(self.resource, self.user_id, '1234',
                                     self.record)
        retrieved = self.storage.get(self.resource, self.user_id, '1234')
        self.assertEquals(retrieved, record)

    def test_update_overwrites_record_id(self):
        self.record['id'] = 4567
        self.storage.update(self.resource, self.user_id, '1234', self.record)
        retrieved = self.storage.get(self.resource, self.user_id, '1234')
        self.assertEquals(retrieved['id'], '1234')

    def test_delete_works_properly(self):
        stored = self.storage.create(self.resource, self.user_id, self.record)
        self.storage.delete(self.resource, self.user_id, stored['id'])
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            self.resource, self.user_id, stored['id']  # Shouldn't exist.
        )

    def test_delete_raise_when_unknown(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.delete,
            self.resource, self.user_id, '1234'
        )

    def test_get_all_return_all_values(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x
            self.storage.create(self.resource, self.user_id, record)

        records, total_records = self.storage.get_all(self.resource,
                                                      self.user_id)
        self.assertEquals(len(records), 10)
        self.assertEquals(len(records), total_records)

    def test_get_all_handle_limit(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x
            self.storage.create(self.resource, self.user_id, record)

        records, total_records = self.storage.get_all(self.resource,
                                                      self.user_id,
                                                      include_deleted=True,
                                                      limit=2)
        self.assertEqual(total_records, 10)
        self.assertEqual(len(records), 2)

    def test_get_all_handle_sorting_on_id(self):
        for x in range(3):
            self.storage.create(self.resource, self.user_id, self.record)
        sorting = [Sort('id', 1)]
        records, _ = self.storage.get_all(self.resource,
                                          self.user_id,
                                          sorting=sorting)
        self.assertTrue(records[0]['id'] < records[-1]['id'])

    def test_get_all_handle_a_pagination_rules(self):
        for x in range(10):
            record = dict(self.record)
            record['id'] = x
            record["number"] = x % 3
            self.storage.create(self.resource, self.user_id, record)

        records, total_records = self.storage.get_all(
            self.resource, self.user_id, pagination_rules=[
                [Filter('number', 1, utils.COMPARISON.GT)]
            ])
        self.assertEqual(total_records, 10)
        self.assertEqual(len(records), 3)

    def test_get_all_handle_all_pagination_rules(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x % 3
            last_record = self.storage.create(self.resource, self.user_id,
                                              record)

        records, total_records = self.storage.get_all(
            self.resource, self.user_id, pagination_rules=[
                [Filter('number', 1, utils.COMPARISON.GT)],
                [Filter('id', last_record['id'], utils.COMPARISON.EQ)]

            ])
        self.assertEqual(total_records, 10)
        self.assertEqual(len(records), 4)


class TimestampsTest(object):
    def test_timestamp_are_incremented_on_create(self):
        self.storage.create(self.resource, self.user_id, self.record)  # init
        before = self.storage.collection_timestamp(self.resource, self.user_id)
        self.storage.create(self.resource, self.user_id, self.record)
        after = self.storage.collection_timestamp(self.resource, self.user_id)
        self.assertTrue(before < after)

    def test_timestamp_are_incremented_on_update(self):
        stored = self.storage.create(self.resource, self.user_id, self.record)
        _id = stored['id']
        before = self.storage.collection_timestamp(self.resource, self.user_id)
        self.storage.update(self.resource, self.user_id, _id, self.record)
        after = self.storage.collection_timestamp(self.resource, self.user_id)
        self.assertTrue(before < after)

    def test_timestamp_are_incremented_on_delete(self):
        stored = self.storage.create(self.resource, self.user_id, self.record)
        _id = stored['id']
        before = self.storage.collection_timestamp(self.resource, self.user_id)
        self.storage.delete(self.resource, self.user_id, _id)
        after = self.storage.collection_timestamp(self.resource, self.user_id)
        self.assertTrue(before < after)

    def test_timestamps_are_unique(self):
        obtained = []

        def create_item():
            for i in range(100):
                record = self.storage.create(
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

    def test_collection_timestamp_returns_now_when_collection_is_empty(self):
        before = utils.msec_time()
        time.sleep(0.001)  # 1 msec
        now = self.storage.collection_timestamp(self.resource, self.user_id)
        time.sleep(0.001)  # 1 msec
        after = utils.msec_time()
        self.assertTrue(before < now < after,
                        '%s < %s < %s' % (before, now, after))

    def test_the_timestamp_are_based_on_real_time_milliseconds(self):
        before = utils.msec_time()
        time.sleep(0.001)  # 1 msec
        record = self.storage.create(self.resource, self.user_id, {})
        now = record['last_modified']
        time.sleep(0.001)  # 1 msec
        after = utils.msec_time()
        self.assertTrue(before < now < after,
                        '%s < %s < %s' % (before, now, after))

    def test_timestamp_are_always_incremented_above_existing_value(self):
        # Create a record with normal clock
        record = self.storage.create(self.resource, self.user_id, {})
        current = record['last_modified']

        # Patch the clock to return a time in the past, before the big bang
        with mock.patch('cliquet.utils.msec_time') as time_mocked:
            time_mocked.return_value = -1

            record = self.storage.create(self.resource, self.user_id, {})
            after = record['last_modified']

        # Expect the last one to be based on the highest value
        self.assertTrue(0 < current < after,
                        '0 < %s < %s' % (current, after))


class FieldsUnicityTest(object):
    def setUp(self):
        super(FieldsUnicityTest, self).setUp()
        self.resource.mapping.Options.unique_fields = ('phone',)

    def create_record(self, record=None, user_id=None):
        record = record or {'phone': '0033677'}
        user_id = user_id or self.user_id
        return self.storage.create(self.resource, user_id, record)

    def test_cannot_insert_duplicate_field(self):
        self.create_record()
        self.assertRaises(exceptions.UnicityError,
                          self.create_record)

    def test_unicity_exception_gives_record_and_field(self):
        record = self.create_record()
        try:
            self.create_record()
        except exceptions.UnicityError as e:
            error = e
        self.assertEqual(error.field, 'phone')
        self.assertDictEqual(error.record, record)

    def test_unicity_is_by_user(self):
        self.create_record()
        self.create_record(user_id='alice')  # not raising

    def test_unicity_is_for_non_null_values(self):
        self.create_record({'phone': None})
        self.create_record({'phone': None})  # not raising

    def test_unicity_does_not_apply_to_deleted_records(self):
        record = self.create_record()
        self.storage.delete(self.resource, self.user_id, record['id'])
        self.create_record()  # not raising

    def test_unicity_applies_to_one_of_all_fields_specified(self):
        self.resource.mapping.Options.unique_fields = ('phone', 'line')
        self.create_record({'phone': 'abc', 'line': '1'})
        self.assertRaises(exceptions.UnicityError,
                          self.create_record,
                          {'phone': 'efg', 'line': '1'})

    def test_updating_with_same_id_does_not_raise_unicity_error(self):
        record = self.create_record()
        self.storage.update(self.resource, self.user_id, record['id'], record)

    def test_updating_raises_unicity_error(self):
        self.create_record({'phone': 'number'})
        record = self.create_record()
        self.assertRaises(exceptions.UnicityError,
                          self.storage.update,
                          self.resource,
                          self.user_id,
                          record['id'],
                          {'phone': 'number'})


class DeletedRecordsTest(object):
    def create_and_delete_record(self, record=None):
        """Helper to create and delete a record."""
        record = record or {'challenge': 'accepted'}
        record = self.storage.create(self.resource, self.user_id, record)
        return self.storage.delete(self.resource, self.user_id, record['id'])

    def test_get_should_not_return_deleted_items(self):
        record = self.create_and_delete_record()
        self.assertRaises(exceptions.RecordNotFoundError,
                          self.storage.get,
                          self.resource,
                          self.user_id,
                          record['id'])

    def test_deleting_a_deleted_item_should_raise_not_found(self):
        record = self.create_and_delete_record()
        self.assertRaises(exceptions.RecordNotFoundError,
                          self.storage.delete,
                          self.resource,
                          self.user_id,
                          record['id'])

    def test_deleted_items_have_deleted_set_to_true(self):
        record = self.create_and_delete_record()
        self.assertTrue(record['deleted'])

    def test_deleted_items_have_only_basic_fields(self):
        record = self.create_and_delete_record()
        self.assertIn('id', record)
        self.assertIn('last_modified', record)
        self.assertNotIn('challenge', record)

    def test_last_modified_of_a_deleted_item_is_deletion_time(self):
        before = self.storage.collection_timestamp(self.resource, self.user_id)
        record = self.create_and_delete_record()
        now = self.storage.collection_timestamp(self.resource, self.user_id)
        self.assertEqual(now, record['last_modified'])
        self.assertTrue(before < record['last_modified'])

    def test_get_all_does_not_include_deleted_items_by_default(self):
        self.create_and_delete_record()
        records, _ = self.storage.get_all(self.resource, self.user_id)
        self.assertEqual(len(records), 0)

    def test_get_all_count_does_not_include_deleted_items(self):
        self.create_and_delete_record()
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              include_deleted=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_get_all_can_return_deleted_items(self):
        record = self.create_and_delete_record()
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          include_deleted=True)
        deleted = records[0]
        self.assertEqual(deleted['id'], record['id'])
        self.assertEqual(deleted['last_modified'], record['last_modified'])
        self.assertEqual(deleted['deleted'], True)
        self.assertNotIn('challenge', deleted)

    def test_delete_all_keeps_track_of_deleted_records(self):
        self.create_and_delete_record()
        self.storage.delete_all(self.resource, self.user_id)
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              include_deleted=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    #
    # Sorting
    #

    def test_sorting_on_last_modified_applies_to_deleted_items(self):
        first = last = None
        for i in range(20, 0, -1):
            record = self.create_and_delete_record()
            first = record if i == 1 else first
            last = record if i == 20 else last

        sorting = [Sort('last_modified', -1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting,
                                          include_deleted=True)

        self.assertDictEqual(records[0], first)
        self.assertDictEqual(records[-1], last)

    def test_sorting_on_last_modified_mixes_deleted_records(self):
        self.create_and_delete_record()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        sorting = [Sort('last_modified', 1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting,
                                          include_deleted=True)

        self.assertIn('deleted', records[0])
        self.assertNotIn('deleted', records[1])
        self.assertIn('deleted', records[2])

    def test_sorting_on_arbitrary_field_groups_deleted_at_last(self):
        self.storage.create(self.resource, self.user_id, {'status': 0})
        self.create_and_delete_record({'status': 1})
        self.create_and_delete_record({'status': 2})

        sorting = [Sort('status', 1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting,
                                          include_deleted=True)
        self.assertNotIn('deleted', records[0])
        self.assertIn('deleted', records[1])
        self.assertIn('deleted', records[2])

    def test_support_sorting_on_deleted_field_groups_deleted_at_first(self):
        # Respect boolean sort order
        self.create_and_delete_record()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        sorting = [Sort('deleted', 1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting,
                                          include_deleted=True)
        self.assertIn('deleted', records[0])
        self.assertIn('deleted', records[1])
        self.assertNotIn('deleted', records[2])

    #
    # Filtering
    #

    def test_filtering_on_last_modified_applies_to_deleted_items(self):
        r = self.create_and_delete_record()
        before = r['last_modified']
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters = [Filter('last_modified', before, utils.COMPARISON.GT)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 2)
        self.assertEqual(count, 1)

    def test_filtering_on_arbitrary_field_excludes_deleted_records(self):
        self.storage.create(self.resource, self.user_id, {'status': 0})
        self.create_and_delete_record({'status': 1})
        self.create_and_delete_record({'status': 2})

        filters = [Filter('status', 0, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 1)

    def test_support_filtering_on_deleted_field(self):
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters = [Filter('deleted', True, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertIn('deleted', records[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_support_filtering_out_on_deleted_field(self):
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters = [Filter('deleted', True, utils.COMPARISON.NOT)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertNotIn('deleted', records[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 1)

    def test_return_empty_set_if_filtering_on_deleted_false(self):
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters = [Filter('deleted', False, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 0)
        self.assertEqual(count, 0)

    def test_return_empty_set_if_filtering_on_deleted_without_include(self):
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters = [Filter('deleted', True, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters)
        self.assertEqual(len(records), 0)
        self.assertEqual(count, 0)

    #
    # Pagination
    #

    def test_pagination_rules_on_last_modified_apply_to_deleted_records(self):
        for i in range(15):
            if i % 2 == 0:
                self.create_and_delete_record()
            else:
                self.storage.create(self.resource, self.user_id, {})

        pagination = [[Filter('last_modified', 0, utils.COMPARISON.GT)]]
        sorting = [Sort('last_modified', 1)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              sorting=sorting,
                                              pagination_rules=pagination,
                                              limit=5,
                                              include_deleted=True)
        self.assertEqual(len(records), 5)
        self.assertEqual(count, 7)
        self.assertIn('deleted', records[0])
        self.assertNotIn('deleted', records[1])


class StorageTest(ThreadMixin,
                  FieldsUnicityTest,
                  TimestampsTest,
                  DeletedRecordsTest,
                  BaseTestStorage):
    """Compound of all storage tests."""
    pass


class MemoryStorageTest(StorageTest, unittest.TestCase):
    backend = memory

    def test_ping_returns_an_error_if_unavailable(self):
        pass

    def test_default_generator(self):
        self.assertEqual(type(self.storage.id_generator()), six.text_type)

    def test_custom_generator(self):
        def l(x):
            return x
        storage = self.storage.__class__(id_generator=l)
        self.assertEqual(storage.id_generator, l)


class RedisStorageTest(MemoryStorageTest, unittest.TestCase):
    backend = redisbackend

    def test_get_all_handle_expired_values(self):
        record = '{"id": "foo"}'.encode('utf-8')
        mocked_smember = mock.patch.object(self.storage._client, "smembers",
                                           return_value=['a', 'b'])
        mocked_mget = mock.patch.object(self.storage._client, "mget",
                                        return_value=[record, None])
        with mocked_smember:
            with mocked_mget:
                self.storage.get_all(TestResource(), "alexis")  # not raising

    def test_ping_returns_an_error_if_unavailable(self):
        self.storage._client.setex = mock.MagicMock(
            side_effect=redis.RedisError)
        self.assertFalse(self.storage.ping())


class PostgresqlStorageTest(StorageTest, unittest.TestCase):
    backend = postgresql
    settings = {
        'cliquet.storage_url':
            'postgres://postgres:postgres@localhost:5432/testdb'
    }

    def test_ping_returns_an_error_if_unavailable(self):
        with mock.patch('cliquet.storage.postgresql.psycopg2.connect',
                        side_effect=psycopg2.DatabaseError):
            self.assertFalse(self.storage.ping())

    def test_ping_updates_a_value_in_the_metadata_table(self):
        query = "SELECT value FROM metadata WHERE name='last_heartbeat';"
        with self.storage.connect() as cursor:
            cursor.execute(query)
            before = cursor.fetchone()
        self.storage.ping()
        with self.storage.connect() as cursor:
            cursor.execute(query)
            after = cursor.fetchone()
        self.assertNotEqual(before, after)

    def test_schema_is_not_recreated_from_scratch_if_already_exists(self):
        with mock.patch('cliquet.storage.postgresql.logger.debug') as mocked:
            self.backend.load_from_config(self._get_config())
            message, = mocked.call_args[0]
            self.assertEqual(message, "Detected PostgreSQL storage tables")

    def test_assert_raises_503_when_connection_fails(self):
        # 503 error relies on Pyramid last registry hook
        global_registries.add(self._get_config().registry)

        with mock.patch('cliquet.storage.postgresql.PostgreSQL._check_unicity',
                        side_effect=psycopg2.OperationalError):
            self.assertRaises(httpexceptions.HTTPServiceUnavailable,
                              self.storage.create,
                              self.resource, 'foo', {})

    def test_number_of_fetched_records_can_be_limited_in_settings(self):
        for i in range(4):
            self.create_record({'phone': 'tel-%s' % i})

        results, count = self.storage.get_all(self.resource, self.user_id)
        self.assertEqual(len(results), 4)

        config = self._get_config()
        config.registry.settings['storage.max_fetch_size'] = 2
        limited = self.backend.load_from_config(config)

        results, count = limited.get_all(self.resource, self.user_id)
        self.assertEqual(len(results), 2)

    def test_connection_is_rolledback_if_error_occurs(self):
        failing_execute = mock.Mock(side_effect=psycopg2.Error)
        fake_cursor = mock.MagicMock(execute=failing_execute)
        fake_get_cursor = mock.Mock(return_value=fake_cursor)

        fake_rollback = mock.MagicMock()
        fake_connection = mock.MagicMock(closed=False,
                                         cursor=fake_get_cursor,
                                         rollback=fake_rollback)
        with mock.patch('cliquet.storage.postgresql.psycopg2.connect',
                        return_value=fake_connection):
            self.assertRaises(Exception,
                              self.storage.collection_timestamp,
                              self.resource, 'bar')
            self.assertTrue(fake_rollback.called)
