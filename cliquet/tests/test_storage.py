import time

import mock
import psycopg2
import redis
import requests
import six

from cliquet import utils
from cliquet import schema
from cliquet.storage import (
    exceptions, Filter, memory,
    redis as redisbackend, postgresql, cloud_storage,
    Sort, StorageBase
)

from .support import unittest, ThreadMixin, DummyRequest

RECORD_ID = '472be9ec-26fe-461b-8282-9c4e4b207ab3'


class StorageBaseTest(unittest.TestCase):
    def setUp(self):
        self.storage = StorageBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.storage.initialize_schema,),
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
    request = DummyRequest()


# Share backend instances accross Nosetests test cases.
_backends_instances = {}


class BaseTestStorage(object):
    backend = None

    settings = {}

    def __init__(self, *args, **kwargs):
        super(BaseTestStorage, self).__init__(*args, **kwargs)
        self.storage = _backends_instances.get(self.backend)
        if self.storage is None:
            instance = self.backend.load_from_config(self._get_config())
            self.storage = _backends_instances[self.backend] = instance
            self.storage.initialize_schema()
        self.resource = TestResource()
        self.user_id = '1234'
        self.other_user_id = '5678'
        self.record = {'foo': 'bar'}
        self.client_error_patcher = None

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        return mock.Mock(get_settings=mock.Mock(return_value=settings))

    def tearDown(self):
        mock.patch.stopall()
        super(BaseTestStorage, self).tearDown()
        self.storage.flush()
        self.resource.mapping = TestMapping()

    def test_raises_backend_error_if_error_occurs_on_client(self):
        self.client_error_patcher.start()
        self.assertRaises(exceptions.BackendError,
                          self.storage.get_all,
                          self.resource, self.user_id)

    def test_backend_error_provides_original_exception(self):
        self.client_error_patcher.start()
        try:
            self.storage.get_all(self.resource, self.user_id)
        except exceptions.BackendError as e:
            error = e
        self.assertTrue(isinstance(error.original, Exception))

    def test_backend_error_is_raised_anywhere(self):
        self.client_error_patcher.start()
        calls = [
            (self.storage.flush,),
            (self.storage.collection_timestamp, self.resource, self.user_id),
            (self.storage.create, self.resource, self.user_id, {}),
            (self.storage.get, self.resource, self.user_id, ''),
            (self.storage.update, self.resource, self.user_id, '', {}),
            (self.storage.delete, self.resource, self.user_id, ''),
            (self.storage.delete_all, self.resource, self.user_id),
            (self.storage.get_all, self.resource, self.user_id),
        ]
        for call in calls:
            self.assertRaises(exceptions.BackendError, *call)

    def test_ping_returns_false_if_unavailable(self):
        self.client_error_patcher.start()
        self.assertFalse(self.storage.ping())

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
            # This record id doesn't exist.
            'af04add0-f2b1-431c-a7cc-11285a3be0e1'
        )

    def test_update_creates_a_new_record_when_needed(self):
        unknown_record_id = memory.UUID4Generator()()
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            self.resource,
            self.user_id,
            unknown_record_id
        )
        record = self.storage.update(self.resource, self.user_id,
                                     unknown_record_id, self.record)
        retrieved = self.storage.get(self.resource, self.user_id,
                                     unknown_record_id)
        self.assertEquals(retrieved, record)

    def test_update_overwrites_record_id(self):
        stored = self.storage.create(self.resource, self.user_id, self.record)
        record_id = stored[self.resource.id_field]
        self.record[self.resource.id_field] = memory.UUID4Generator()()
        self.storage.update(self.resource, self.user_id, record_id,
                            self.record)
        retrieved = self.storage.get(self.resource, self.user_id, record_id)
        self.assertEquals(retrieved[self.resource.id_field], record_id)

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
            self.resource, self.user_id, RECORD_ID
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
            record["number"] = x % 3
            self.storage.create(self.resource, self.user_id, record)

        records, total_records = self.storage.get_all(
            self.resource, self.user_id, limit=5, pagination_rules=[
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
            self.resource, self.user_id, limit=5, pagination_rules=[
                [Filter('number', 1, utils.COMPARISON.GT)],
                [Filter('id', last_record['id'], utils.COMPARISON.EQ)],
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
        self.storage.update(self.resource, self.user_id, _id, {'bar': 'foo'})
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
        self.resource.request.headers['Authorization'] = 'Basic %s' % (
            utils.encode64('alice:')
        )
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

    def test_unicity_detection_supports_special_characters(self):
        record = self.create_record()
        values = ['b', 'http://moz.org', u"#131 \u2014 ujson",
                  "C:\\\\win32\\hosts"]
        for value in values:
            self.create_record({'phone': value})
            try:
                error = None
                self.storage.update(self.resource,
                                    self.user_id,
                                    record['id'],
                                    {'phone': value})
            except exceptions.UnicityError as e:
                error = e
            msg = 'UnicityError not raised with %s' % value
            self.assertIsNotNone(error, msg)


class DeletedRecordsTest(object):
    def _get_last_modified_filters(self):
        start = self.storage.collection_timestamp(self.resource, self.user_id)
        return [
            Filter(self.resource.modified_field, start, utils.COMPARISON.GT)
        ]

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
        filters = self._get_last_modified_filters()
        self.create_and_delete_record()
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_get_all_can_return_deleted_items(self):
        filters = self._get_last_modified_filters()
        record = self.create_and_delete_record()
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          filters=filters,
                                          include_deleted=True)
        deleted = records[0]
        self.assertEqual(deleted['id'], record['id'])
        self.assertEqual(deleted['last_modified'], record['last_modified'])
        self.assertEqual(deleted['deleted'], True)
        self.assertNotIn('challenge', deleted)

    def test_delete_all_keeps_track_of_deleted_records(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_record()
        self.storage.delete_all(self.resource, self.user_id)
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_delete_all_deletes_records(self):
        self.storage.create(self.resource, self.user_id, {'foo': 'bar'})
        self.storage.create(self.resource, self.user_id, {'bar': 'baz'})
        self.storage.delete_all(self.resource, self.user_id)
        _, count = self.storage.get_all(self.resource, self.user_id)
        self.assertEqual(count, 0)

    #
    # Sorting
    #

    def test_sorting_on_last_modified_applies_to_deleted_items(self):
        filters = self._get_last_modified_filters()
        first = last = None
        for i in range(20, 0, -1):
            record = self.create_and_delete_record()
            first = record if i == 1 else first
            last = record if i == 20 else last

        sorting = [Sort('last_modified', -1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting, filters=filters,
                                          include_deleted=True)

        self.assertDictEqual(records[0], first)
        self.assertDictEqual(records[-1], last)

    def test_sorting_on_last_modified_mixes_deleted_records(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_record()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        sorting = [Sort('last_modified', 1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting, filters=filters,
                                          include_deleted=True)

        self.assertIn('deleted', records[0])
        self.assertNotIn('deleted', records[1])
        self.assertIn('deleted', records[2])

    def test_sorting_on_arbitrary_field_groups_deleted_at_last(self):
        filters = self._get_last_modified_filters()
        self.storage.create(self.resource, self.user_id, {'status': 0})
        self.create_and_delete_record({'status': 1})
        self.create_and_delete_record({'status': 2})

        sorting = [Sort('status', 1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting, filters=filters,
                                          include_deleted=True)
        self.assertNotIn('deleted', records[0])
        self.assertIn('deleted', records[1])
        self.assertIn('deleted', records[2])

    def test_support_sorting_on_deleted_field_groups_deleted_at_first(self):
        filters = self._get_last_modified_filters()
        # Respect boolean sort order
        self.create_and_delete_record()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        sorting = [Sort('deleted', 1)]
        records, _ = self.storage.get_all(self.resource, self.user_id,
                                          sorting=sorting, filters=filters,
                                          include_deleted=True)
        self.assertIn('deleted', records[0])
        self.assertIn('deleted', records[1])
        self.assertNotIn('deleted', records[2])

    #
    # Filtering
    #

    def test_filtering_on_last_modified_applies_to_deleted_items(self):
        self.create_and_delete_record()
        filters = self._get_last_modified_filters()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 2)
        self.assertEqual(count, 1)

    def test_filtering_on_arbitrary_field_excludes_deleted_records(self):
        filters = self._get_last_modified_filters()
        self.storage.create(self.resource, self.user_id, {'status': 0})
        self.create_and_delete_record({'status': 0})

        filters += [Filter('status', 0, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 1)

    def test_support_filtering_on_deleted_field(self):
        filters = self._get_last_modified_filters()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters += [Filter('deleted', True, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertIn('deleted', records[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_support_filtering_out_on_deleted_field(self):
        filters = self._get_last_modified_filters()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters += [Filter('deleted', True, utils.COMPARISON.NOT)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              filters=filters,
                                              include_deleted=True)
        self.assertNotIn('deleted', records[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 1)

    def test_return_empty_set_if_filtering_on_deleted_false(self):
        filters = self._get_last_modified_filters()
        self.storage.create(self.resource, self.user_id, {})
        self.create_and_delete_record()

        filters += [Filter('deleted', False, utils.COMPARISON.EQ)]
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
        filters = self._get_last_modified_filters()
        for i in range(15):
            if i % 2 == 0:
                self.create_and_delete_record()
            else:
                self.storage.create(self.resource, self.user_id, {})

        pagination = [[Filter('last_modified', 314, utils.COMPARISON.GT)]]
        sorting = [Sort('last_modified', 1)]
        records, count = self.storage.get_all(self.resource, self.user_id,
                                              sorting=sorting,
                                              pagination_rules=pagination,
                                              limit=5, filters=filters,
                                              include_deleted=True)
        self.assertEqual(len(records), 5)
        self.assertEqual(count, 7)
        self.assertIn('deleted', records[0])
        self.assertNotIn('deleted', records[1])


class UserRecordAccessTest(object):
    def create_record(self):
        return self.storage.create(self.resource, self.user_id,
                                   {'foo': 'bar'})

    def authenticate_as(self, user_id):
        self.resource.request.headers['Authorization'] = 'Basic %s' % (
            utils.encode64('%s:' % user_id)
        )

    def test_users_cannot_access_other_users_record(self):
        record = self.create_record()
        self.authenticate_as(self.other_user_id)
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            self.resource, self.other_user_id, record['id'])

    def test_users_cannot_delete_other_users_record(self):
        record = self.create_record()
        self.authenticate_as(self.other_user_id)
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.delete,
            self.resource, self.other_user_id, record['id'])

    def test_users_cannot_update_other_users_record(self):
        self.authenticate_as(self.user_id)
        record = self.create_record()
        new_record = {"another": "record"}
        # Cloud storage backend ignores the passer userid and read it from the
        # resource request.
        self.authenticate_as(self.other_user_id)
        self.storage.update(self.resource, self.other_user_id, record['id'],
                            new_record)
        self.authenticate_as(self.user_id)
        not_updated = self.storage.get(self.resource, self.user_id,
                                       record['id'])

        self.assertNotIn("another", not_updated)


class StorageTest(ThreadMixin,
                  FieldsUnicityTest,
                  TimestampsTest,
                  DeletedRecordsTest,
                  UserRecordAccessTest,
                  BaseTestStorage):
    """Compound of all storage tests."""
    pass


class MemoryStorageTest(StorageTest, unittest.TestCase):
    backend = memory

    def __init__(self, *args, **kwargs):
        super(MemoryStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.Mock(
            side_effect=exceptions.BackendError)

    def test_backend_error_provides_original_exception(self):
        pass

    def test_raises_backend_error_if_error_occurs_on_client(self):
        pass

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_ping_returns_false_if_unavailable(self):
        pass

    def test_default_generator(self):
        self.assertEqual(type(self.storage.id_generator()), six.text_type)

    def test_custom_generator(self):
        def l(x):
            return x
        storage = self.storage.__class__(id_generator=l, max_connections=1)
        self.assertEqual(storage.id_generator, l)


class RedisStorageTest(MemoryStorageTest, unittest.TestCase):
    backend = redisbackend
    settings = {
        'cliquet.storage_pool_size': 50,
        'cliquet.storage_url': ''
    }

    def __init__(self, *args, **kwargs):
        super(RedisStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.storage._client,
            'execute_command',
            side_effect=redis.RedisError)

    def test_ping_returns_false_if_unavailable(self):
        StorageTest.test_ping_returns_false_if_unavailable(self)

    def test_backend_error_provides_original_exception(self):
        StorageTest.test_backend_error_provides_original_exception(self)

    def test_raises_backend_error_if_error_occurs_on_client(self):
        StorageTest.test_raises_backend_error_if_error_occurs_on_client(self)

    def test_backend_error_is_raised_anywhere(self):
        with mock.patch.object(self.storage._client, 'pipeline',
                               side_effect=redis.RedisError):
            StorageTest.test_backend_error_is_raised_anywhere(self)

    def test_get_all_handle_expired_values(self):
        record = '{"id": "foo"}'.encode('utf-8')
        mocked_smember = mock.patch.object(self.storage._client, "smembers",
                                           return_value=['a', 'b'])
        mocked_mget = mock.patch.object(self.storage._client, "mget",
                                        return_value=[record, None])
        with mocked_smember:
            with mocked_mget:
                self.storage.get_all(TestResource(), "alexis")  # not raising


class PostgresqlStorageTest(StorageTest, unittest.TestCase):
    backend = postgresql
    settings = {
        'cliquet.storage_pool_size': 10,
        'cliquet.storage_max_fetch_size': 10000,
        'cliquet.storage_url':
            'postgres://postgres:postgres@localhost:5432/testdb'
    }

    def __init__(self, *args, **kwargs):
        super(PostgresqlStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.storage.pool,
            'getconn',
            side_effect=psycopg2.DatabaseError)

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
            self.storage.initialize_schema()
            message, = mocked.call_args[0]
            self.assertEqual(message, "Detected PostgreSQL storage tables")

    def test_warns_if_database_is_not_utc(self):
        with self.storage.connect() as cursor:
            cursor.execute("ALTER ROLE postgres SET TIME ZONE 'Europe/Paris';")

        with mock.patch('cliquet.storage.postgresql.warnings.warn') as mocked:
            self.backend.load_from_config(self._get_config())
            mocked.assert_called()

        with self.storage.connect() as cursor:
            cursor.execute("ALTER ROLE postgres SET TIME ZONE 'UTC';")

    def test_number_of_fetched_records_can_be_limited_in_settings(self):
        for i in range(4):
            self.create_record({'phone': 'tel-%s' % i})

        results, count = self.storage.get_all(self.resource, self.user_id)
        self.assertEqual(len(results), 4)

        settings = self.settings.copy()
        settings['cliquet.storage_max_fetch_size'] = 2
        config = self._get_config(settings=settings)
        limited = self.backend.load_from_config(config)

        results, count = limited.get_all(self.resource, self.user_id)
        self.assertEqual(len(results), 2)

    def test_connection_is_rolledback_if_error_occurs(self):
        with self.storage.connect() as cursor:
            query = "DELETE FROM metadata WHERE name = 'roll';"
            cursor.execute(query)

        try:
            with self.storage.connect() as cursor:
                query = "INSERT INTO metadata VALUES ('roll', 'back');"
                cursor.execute(query)
                cursor.connection.commit()

                query = "INSERT INTO metadata VALUES ('roll', 'rock');"
                cursor.execute(query)

                raise psycopg2.Error()
        except exceptions.BackendError:
            pass

        with self.storage.connect() as cursor:
            query = "SELECT COUNT(*) FROM metadata WHERE name = 'roll';"
            cursor.execute(query)
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_pool_object_is_shared_among_backend_instances(self):
        config = self._get_config()
        storage1 = self.backend.load_from_config(config)
        storage2 = self.backend.load_from_config(config)
        self.assertEqual(id(storage1.pool), id(storage2.pool))

    def test_pool_object_is_shared_among_every_backends(self):
        config = self._get_config()
        storage1 = self.backend.load_from_config(config)
        subclass = type('backend', (postgresql.PostgreSQLClient,), {})
        storage2 = subclass(user='postgres', password='postgres',
                            host='localhost', database='testdb',
                            pool_size=10)
        self.assertEqual(id(storage1.pool), id(storage2.pool))

    def test_warns_if_configured_pool_size_differs_for_same_backend_type(self):
        self.backend.load_from_config(self._get_config())
        settings = self.settings.copy()
        settings['cliquet.storage_pool_size'] = 1
        with mock.patch('cliquet.storage.postgresql.warnings.warn') as mocked:
            self.backend.load_from_config(self._get_config(settings=settings))
            mocked.assert_called()


class CloudStorageTest(StorageTest, unittest.TestCase):
    backend = cloud_storage
    settings = {
        'cliquet.storage_url':
            'http://localhost:8888'
    }

    def setUp(self):
        super(CloudStorageTest, self).setUp()
        self.resource.request.headers = {'Authorization': 'Basic Ym9iOg=='}
        self.client_error_patcher = mock.patch.object(
            self.storage._client,
            'request',
            side_effect=requests.ConnectionError)

    def test_raises_backenderror_when_remote_returns_500(self):
        with mock.patch.object(self.storage._client, 'request') as mocked:
            error_response = requests.models.Response()
            error_response.status_code = 500
            error_response._content_consumed = True
            error_response._content = u'Internal Error'.encode('utf8')
            mocked.return_value = error_response
            self.assertRaises(exceptions.BackendError,
                              self.storage.get_all,
                              self.resource,
                              self.user_id)
