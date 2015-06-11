import time

import mock
import psycopg2
import redis

from cliquet import utils
from cliquet.storage import (
    exceptions, Filter, generators, memory,
    redis as redisbackend, postgresql,
    Sort, StorageBase
)

from .support import unittest, ThreadMixin, DummyRequest, skip_if_travis


RECORD_ID = '472be9ec-26fe-461b-8282-9c4e4b207ab3'


class GeneratorTest(unittest.TestCase):
    def test_generic_has_mandatory_override(self):
        self.assertRaises(NotImplementedError, generators.Generator)

    def test_id_generator_must_respect_storage_backends(self):
        class Dumb(generators.Generator):
            def __call__(self):
                return '*' * 80

        self.assertRaises(AssertionError, Dumb)

    def test_uuid4_generator_has_accurate_pattern(self):
        generator = generators.UUID4()
        self.assertTrue(generator.match(RECORD_ID))
        fake_uuid4 = '00000000-0000-5000-a000-000000000000'
        self.assertFalse(generator.match(fake_uuid4))
        fake_uuid4 = '00000000-0000-4000-e000-000000000000'
        self.assertFalse(generator.match(fake_uuid4))


class StorageBaseTest(unittest.TestCase):
    def setUp(self):
        self.storage = StorageBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.storage.initialize_schema,),
            (self.storage.flush,),
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

    def test_backend_error_message_provides_given_message_if_defined(self):
        error = exceptions.BackendError(message="Connection Error")
        self.assertEqual(str(error), "Connection Error")

    def test_backenderror_message_default_to_original_exception_message(self):
        error = exceptions.BackendError(ValueError("Pool Error"))
        self.assertEqual(str(error), "ValueError: Pool Error")


class BaseTestStorage(object):
    backend = None

    settings = {}

    def __init__(self, *args, **kwargs):
        super(BaseTestStorage, self).__init__(*args, **kwargs)
        self.storage = self.backend.load_from_config(self._get_config())
        self.storage.initialize_schema()
        self.id_field = 'id'
        self.modified_field = 'last_modified'
        self.client_error_patcher = None

    def _get_config(self, settings=None):
        """Mock Pyramid config object.
        """
        if settings is None:
            settings = self.settings
        return mock.Mock(get_settings=mock.Mock(return_value=settings))

    def setUp(self):
        super(BaseTestStorage, self).setUp()
        self.record = {'foo': 'bar'}
        self.storage_kw = {
            'collection_id': 'test',
            'parent_id': '1234',
            'auth': 'Basic bWF0OjI='
        }
        self.other_parent_id = '5678'
        self.other_auth = 'Basic bWF0OjE='

    def tearDown(self):
        mock.patch.stopall()
        super(BaseTestStorage, self).tearDown()
        self.storage.flush()

    def create_record(self, record=None, id_generator=None,
                      unique_fields=None, **kwargs):
        record = record or self.record
        kw = self.storage_kw.copy()
        kw.update(**kwargs)
        return self.storage.create(record=record,
                                   id_generator=id_generator,
                                   unique_fields=unique_fields,
                                   **kw)

    def test_raises_backend_error_if_error_occurs_on_client(self):
        self.client_error_patcher.start()
        self.assertRaises(exceptions.BackendError,
                          self.storage.get_all,
                          **self.storage_kw)

    def test_backend_error_provides_original_exception(self):
        self.client_error_patcher.start()
        try:
            self.storage.get_all(**self.storage_kw)
        except exceptions.BackendError as e:
            error = e
        self.assertTrue(isinstance(error.original, Exception))

    def test_backend_error_is_raised_anywhere(self):
        self.client_error_patcher.start()
        calls = [
            (self.storage.collection_timestamp, {}),
            (self.storage.create, dict(record={})),
            (self.storage.get, dict(object_id={})),
            (self.storage.update, dict(object_id='', record={})),
            (self.storage.delete, dict(object_id='')),
            (self.storage.delete_all, {}),
            (self.storage.get_all, {}),
        ]
        for call, kwargs in calls:
            kwargs.update(**self.storage_kw)
            self.assertRaises(exceptions.BackendError, call, **kwargs)
        self.assertRaises(exceptions.BackendError,
                          self.storage.flush,
                          auth=self.other_auth)

    def test_ping_returns_false_if_unavailable(self):
        request = DummyRequest()
        request.headers['Authorization'] = self.storage_kw['auth']

        with mock.patch('cliquet.storage.random.random', return_value=0.7):
            self.storage.ping(request)

        self.client_error_patcher.start()
        with mock.patch('cliquet.storage.random.random', return_value=0.7):
            self.assertFalse(self.storage.ping(request))
        with mock.patch('cliquet.storage.random.random', return_value=0.5):
            self.assertFalse(self.storage.ping(request))

    def test_ping_returns_true_when_working(self):
        request = DummyRequest()
        request.headers['Authorization'] = 'Basic bWF0OjI='
        with mock.patch('cliquet.storage.random.random', return_value=0.7):
            self.assertTrue(self.storage.ping(request))
        with mock.patch('cliquet.storage.random.random', return_value=0.5):
            self.assertTrue(self.storage.ping(request))

    def test_create_adds_the_record_id(self):
        record = self.create_record()
        self.assertIsNotNone(record['id'])

    def test_create_works_as_expected(self):
        stored = self.create_record()
        retrieved = self.storage.get(object_id=stored['id'], **self.storage_kw)
        self.assertEquals(retrieved, stored)

    def test_create_copies_the_record_before_modifying_it(self):
        self.create_record()
        self.assertEquals(self.record.get('id'), None)

    def test_create_uses_the_resource_id_generator(self):
        record = self.create_record(id_generator=lambda: RECORD_ID)
        self.assertEquals(record['id'], RECORD_ID)

    def test_create_does_not_overwrite_the_provided_id(self):
        record = self.record.copy()
        record[self.id_field] = RECORD_ID
        stored = self.create_record(record=record)
        self.assertEqual(stored[self.id_field], RECORD_ID)

    def test_create_raise_unicity_error_if_provided_id_exists(self):
        record = self.record.copy()
        record[self.id_field] = RECORD_ID
        self.create_record(record=record)
        record = self.record.copy()
        record[self.id_field] = RECORD_ID
        self.assertRaises(exceptions.UnicityError,
                          self.create_record,
                          record=record)

    def test_get_raise_on_record_not_found(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            object_id=RECORD_ID,
            **self.storage_kw
        )

    def test_update_creates_a_new_record_when_needed(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            object_id=RECORD_ID,
            **self.storage_kw
        )
        record = self.storage.update(object_id=RECORD_ID,
                                     record=self.record,
                                     **self.storage_kw)
        retrieved = self.storage.get(object_id=RECORD_ID,
                                     **self.storage_kw)
        self.assertEquals(retrieved, record)

    def test_update_overwrites_record_id(self):
        stored = self.create_record()
        record_id = stored[self.id_field]
        self.record[self.id_field] = 'this-will-be-ignored'
        self.storage.update(object_id=record_id, record=self.record,
                            **self.storage_kw)
        retrieved = self.storage.get(object_id=record_id, **self.storage_kw)
        self.assertEquals(retrieved[self.id_field], record_id)

    def test_delete_works_properly(self):
        stored = self.create_record()
        self.storage.delete(object_id=stored['id'], **self.storage_kw)
        self.assertRaises(  # Shouldn't exist.
            exceptions.RecordNotFoundError,
            self.storage.get,
            object_id=stored['id'],
            **self.storage_kw
        )

    def test_delete_raise_when_unknown(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.delete,
            object_id=RECORD_ID,
            **self.storage_kw
        )

    def test_get_all_return_all_values(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x
            self.create_record(record)

        records, total_records = self.storage.get_all(**self.storage_kw)
        self.assertEquals(len(records), 10)
        self.assertEquals(len(records), total_records)

    def test_get_all_handle_limit(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x
            self.create_record(record)

        records, total_records = self.storage.get_all(include_deleted=True,
                                                      limit=2,
                                                      **self.storage_kw)
        self.assertEqual(total_records, 10)
        self.assertEqual(len(records), 2)

    def test_get_all_handle_sorting_on_id(self):
        for x in range(3):
            self.create_record()
        sorting = [Sort('id', 1)]
        records, _ = self.storage.get_all(sorting=sorting,
                                          **self.storage_kw)
        self.assertTrue(records[0]['id'] < records[-1]['id'])

    def test_get_all_handle_a_pagination_rules(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x % 3
            self.create_record(record)

        records, total_records = self.storage.get_all(
            limit=5,
            pagination_rules=[
                [Filter('number', 1, utils.COMPARISON.GT)]
            ], **self.storage_kw)
        self.assertEqual(total_records, 10)
        self.assertEqual(len(records), 3)

    def test_get_all_handle_all_pagination_rules(self):
        for x in range(10):
            record = dict(self.record)
            record["number"] = x % 3
            last_record = self.create_record(record)

        records, total_records = self.storage.get_all(
            limit=5, pagination_rules=[
                [Filter('number', 1, utils.COMPARISON.GT)],
                [Filter('id', last_record['id'], utils.COMPARISON.EQ)],
            ], **self.storage_kw)
        self.assertEqual(total_records, 10)
        self.assertEqual(len(records), 4)


class TimestampsTest(object):
    def test_timestamp_are_incremented_on_create(self):
        self.create_record()  # init
        before = self.storage.collection_timestamp(**self.storage_kw)
        self.create_record()
        after = self.storage.collection_timestamp(**self.storage_kw)
        self.assertTrue(before < after)

    def test_timestamp_are_incremented_on_update(self):
        stored = self.create_record()
        _id = stored['id']
        before = self.storage.collection_timestamp(**self.storage_kw)
        self.storage.update(object_id=_id, record={'bar': 'foo'},
                            **self.storage_kw)
        after = self.storage.collection_timestamp(**self.storage_kw)
        self.assertTrue(before < after)

    def test_timestamp_are_incremented_on_delete(self):
        stored = self.create_record()
        _id = stored['id']
        before = self.storage.collection_timestamp(**self.storage_kw)
        self.storage.delete(object_id=_id, **self.storage_kw)
        after = self.storage.collection_timestamp(**self.storage_kw)
        self.assertTrue(before < after)

    @skip_if_travis
    def test_timestamps_are_unique(self):
        obtained = []

        def create_item():
            for i in range(100):
                record = self.create_record()
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
        now = self.storage.collection_timestamp(**self.storage_kw)
        time.sleep(0.001)  # 1 msec
        after = utils.msec_time()
        self.assertTrue(before < now < after,
                        '%s < %s < %s' % (before, now, after))

    def test_the_timestamp_are_based_on_real_time_milliseconds(self):
        before = utils.msec_time()
        time.sleep(0.001)  # 1 msec
        record = self.create_record()
        now = record['last_modified']
        time.sleep(0.001)  # 1 msec
        after = utils.msec_time()
        self.assertTrue(before < now < after,
                        '%s < %s < %s' % (before, now, after))

    def test_timestamp_are_always_incremented_above_existing_value(self):
        # Create a record with normal clock
        record = self.create_record()
        current = record['last_modified']

        # Patch the clock to return a time in the past, before the big bang
        with mock.patch('cliquet.utils.msec_time') as time_mocked:
            time_mocked.return_value = -1

            record = self.create_record()
            after = record['last_modified']

        # Expect the last one to be based on the highest value
        self.assertTrue(0 < current < after,
                        '0 < %s < %s' % (current, after))


class FieldsUnicityTest(object):
    def test_does_not_fail_if_no_unique_fields_at_all(self):
        self.create_record({'phone': '0033677'})
        self.create_record({'phone': '0033677'}, unique_fields=tuple())

    def test_cannot_insert_duplicate_field(self):
        self.create_record({'phone': '0033677'})
        self.assertRaises(exceptions.UnicityError,
                          self.create_record,
                          {'phone': '0033677'},
                          unique_fields=('phone',))

    def test_unicity_exception_gives_record_and_field(self):
        record = self.create_record({'phone': '0033677'})
        try:
            self.create_record({'phone': '0033677'},
                               unique_fields=('phone',))
        except exceptions.UnicityError as e:
            error = e
        self.assertEqual(error.field, 'phone')
        self.assertDictEqual(error.record, record)

    def test_unicity_is_by_parent_id(self):
        self.create_record({'phone': '0033677'})
        self.create_record({'phone': '0033677'},
                           unique_fields=('phone',),
                           parent_id=self.other_parent_id,
                           auth=self.other_auth)  # not raising

    def test_unicity_is_for_non_null_values(self):
        r = self.create_record({'phone': None}, unique_fields=('phone',))
        # not raising with None value
        self.create_record({'phone': None}, unique_fields=('phone',))
        self.storage.update(object_id=r['id'], record={'phone': None},
                            unique_fields=('phone',), **self.storage_kw)

    def test_unicity_does_not_apply_to_deleted_records(self):
        record = self.create_record({'phone': '0033677'})
        self.storage.delete(object_id=record['id'], **self.storage_kw)
        self.create_record({'phone': None}, unique_fields=('phone',))

    def test_unicity_applies_to_one_of_all_fields_specified(self):
        self.create_record({'phone': 'abc', 'line': '1'})
        self.assertRaises(exceptions.UnicityError,
                          self.create_record,
                          {'phone': 'efg', 'line': '1'},
                          unique_fields=('phone', 'line'))

    def test_updating_with_same_id_does_not_raise_unicity_error(self):
        record = self.create_record({'phone': '0033677'})
        self.storage.update(object_id=record['id'],
                            record=record,
                            unique_fields=('phone',),
                            **self.storage_kw)

    def test_updating_raises_unicity_error(self):
        self.create_record({'phone': 'number'})
        record = self.create_record({'phone': '0033677'})
        self.assertRaises(exceptions.UnicityError,
                          self.storage.update,
                          object_id=record['id'],
                          record={'phone': 'number'},
                          unique_fields=('phone',),
                          **self.storage_kw)

    def test_unicity_detection_supports_special_characters(self):
        record = self.create_record()
        values = ['b', 'http://moz.org', u"#131 \u2014 ujson",
                  "C:\\\\win32\\hosts"]
        for value in values:
            self.create_record({'phone': value})
            try:
                error = None
                self.storage.update(object_id=record['id'],
                                    record={'phone': value},
                                    unique_fields=('phone',),
                                    **self.storage_kw)
            except exceptions.UnicityError as e:
                error = e
            msg = 'UnicityError not raised with %s' % value
            self.assertIsNotNone(error, msg)


class DeletedRecordsTest(object):
    def _get_last_modified_filters(self):
        start = self.storage.collection_timestamp(**self.storage_kw)
        return [
            Filter(self.modified_field, start, utils.COMPARISON.GT)
        ]

    def create_and_delete_record(self, record=None):
        """Helper to create and delete a record."""
        record = record or {'challenge': 'accepted'}
        record = self.create_record(record)
        return self.storage.delete(object_id=record['id'], **self.storage_kw)

    def test_get_should_not_return_deleted_items(self):
        record = self.create_and_delete_record()
        self.assertRaises(exceptions.RecordNotFoundError,
                          self.storage.get,
                          object_id=record['id'],
                          **self.storage_kw)

    def test_deleting_a_deleted_item_should_raise_not_found(self):
        record = self.create_and_delete_record()
        self.assertRaises(exceptions.RecordNotFoundError,
                          self.storage.delete,
                          object_id=record['id'],
                          **self.storage_kw)

    def test_deleted_items_have_deleted_set_to_true(self):
        record = self.create_and_delete_record()
        self.assertTrue(record['deleted'])

    def test_deleted_items_have_only_basic_fields(self):
        record = self.create_and_delete_record()
        self.assertIn('id', record)
        self.assertIn('last_modified', record)
        self.assertNotIn('challenge', record)

    def test_last_modified_of_a_deleted_item_is_deletion_time(self):
        before = self.storage.collection_timestamp(**self.storage_kw)
        record = self.create_and_delete_record()
        now = self.storage.collection_timestamp(**self.storage_kw)
        self.assertEqual(now, record['last_modified'])
        self.assertTrue(before < record['last_modified'])

    def test_get_all_does_not_include_deleted_items_by_default(self):
        self.create_and_delete_record()
        records, _ = self.storage.get_all(**self.storage_kw)
        self.assertEqual(len(records), 0)

    def test_get_all_count_does_not_include_deleted_items(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_record()
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_get_all_can_return_deleted_items(self):
        filters = self._get_last_modified_filters()
        record = self.create_and_delete_record()
        records, _ = self.storage.get_all(filters=filters,
                                          include_deleted=True,
                                          **self.storage_kw)
        deleted = records[0]
        self.assertEqual(deleted['id'], record['id'])
        self.assertEqual(deleted['last_modified'], record['last_modified'])
        self.assertEqual(deleted['deleted'], True)
        self.assertNotIn('challenge', deleted)

    def test_delete_all_keeps_track_of_deleted_records(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_record()
        self.storage.delete_all(**self.storage_kw)
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_delete_all_deletes_records(self):
        self.create_record()
        self.create_record()
        self.storage.delete_all(**self.storage_kw)
        _, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(count, 0)

    def test_delete_all_can_delete_partially(self):
        self.create_record({'foo': 'po'})
        self.create_record()
        filters = [Filter('foo', 'bar', utils.COMPARISON.EQ)]
        self.storage.delete_all(filters=filters, **self.storage_kw)
        _, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(count, 1)

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
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          include_deleted=True,
                                          **self.storage_kw)

        self.assertDictEqual(records[0], first)
        self.assertDictEqual(records[-1], last)

    def test_sorting_on_last_modified_mixes_deleted_records(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_record()
        self.create_record()
        self.create_and_delete_record()

        sorting = [Sort('last_modified', 1)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          include_deleted=True,
                                          **self.storage_kw)

        self.assertIn('deleted', records[0])
        self.assertNotIn('deleted', records[1])
        self.assertIn('deleted', records[2])

    def test_sorting_on_arbitrary_field_groups_deleted_at_last(self):
        filters = self._get_last_modified_filters()
        self.create_record({'status': 0})
        self.create_and_delete_record({'status': 1})
        self.create_and_delete_record({'status': 2})

        sorting = [Sort('status', 1)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          include_deleted=True,
                                          **self.storage_kw)
        self.assertNotIn('deleted', records[0])
        self.assertIn('deleted', records[1])
        self.assertIn('deleted', records[2])

    def test_support_sorting_on_deleted_field_groups_deleted_at_first(self):
        filters = self._get_last_modified_filters()
        # Respect boolean sort order
        self.create_and_delete_record()
        self.create_record()
        self.create_and_delete_record()

        sorting = [Sort('deleted', 1)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          include_deleted=True,
                                          **self.storage_kw)
        self.assertIn('deleted', records[0])
        self.assertIn('deleted', records[1])
        self.assertNotIn('deleted', records[2])

    #
    # Filtering
    #

    def test_filtering_on_last_modified_applies_to_deleted_items(self):
        self.create_and_delete_record()
        filters = self._get_last_modified_filters()
        self.create_record()
        self.create_and_delete_record()

        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 2)
        self.assertEqual(count, 1)

    def test_filtering_on_arbitrary_field_excludes_deleted_records(self):
        filters = self._get_last_modified_filters()
        self.create_record({'status': 0})
        self.create_and_delete_record({'status': 0})

        filters += [Filter('status', 0, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 1)

    def test_support_filtering_on_deleted_field(self):
        filters = self._get_last_modified_filters()
        self.create_record()
        self.create_and_delete_record()

        filters += [Filter('deleted', True, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertIn('deleted', records[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_support_filtering_out_on_deleted_field(self):
        filters = self._get_last_modified_filters()
        self.create_record()
        self.create_and_delete_record()

        filters += [Filter('deleted', True, utils.COMPARISON.NOT)]
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertNotIn('deleted', records[0])
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 1)

    def test_return_empty_set_if_filtering_on_deleted_false(self):
        filters = self._get_last_modified_filters()
        self.create_record()
        self.create_and_delete_record()

        filters += [Filter('deleted', False, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 0)
        self.assertEqual(count, 0)

    def test_return_empty_set_if_filtering_on_deleted_without_include(self):
        self.create_record()
        self.create_and_delete_record()

        filters = [Filter('deleted', True, utils.COMPARISON.EQ)]
        records, count = self.storage.get_all(filters=filters,
                                              **self.storage_kw)
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
                self.create_record()

        pagination = [[Filter('last_modified', 314, utils.COMPARISON.GT)]]
        sorting = [Sort('last_modified', 1)]
        records, count = self.storage.get_all(sorting=sorting,
                                              pagination_rules=pagination,
                                              limit=5, filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 5)
        self.assertEqual(count, 7)
        self.assertIn('deleted', records[0])
        self.assertNotIn('deleted', records[1])


class ParentRecordAccessTest(object):
    def test_parent_cannot_access_other_parent_record(self):
        record = self.create_record()
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.get,
            collection_id=self.storage_kw['collection_id'],
            parent_id=self.other_parent_id,
            object_id=record['id'],
            auth=self.other_auth)

    def test_parent_cannot_delete_other_parent_record(self):
        record = self.create_record()
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.delete,
            collection_id=self.storage_kw['collection_id'],
            parent_id=self.other_parent_id,
            object_id=record['id'],
            auth=self.other_auth)

    def test_parent_cannot_update_other_parent_record(self):
        record = self.create_record()

        new_record = {"another": "record"}
        kw = self.storage_kw.copy()
        kw['parent_id'] = self.other_parent_id
        kw['auth'] = self.other_auth
        self.storage.update(object_id=record['id'], record=new_record, **kw)

        not_updated = self.storage.get(object_id=record['id'],
                                       **self.storage_kw)
        self.assertNotIn("another", not_updated)


class StorageTest(ThreadMixin,
                  FieldsUnicityTest,
                  TimestampsTest,
                  DeletedRecordsTest,
                  ParentRecordAccessTest,
                  BaseTestStorage):
    """Compound of all storage tests."""
    pass


class MemoryStorageTest(StorageTest, unittest.TestCase):
    backend = memory

    def __init__(self, *args, **kwargs):
        super(MemoryStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.storage,
            '_bump_timestamp',
            side_effect=exceptions.BackendError("Segmentation fault."))

    def test_backend_error_provides_original_exception(self):
        pass

    def test_raises_backend_error_if_error_occurs_on_client(self):
        pass

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_backenderror_message_default_to_original_exception_message(self):
        pass


class RedisStorageTest(MemoryStorageTest, unittest.TestCase):
    backend = redisbackend
    settings = {
        'cliquet.storage_pool_size': 50,
        'cliquet.storage_url': ''
    }

    def __init__(self, *args, **kwargs):
        super(RedisStorageTest, self).__init__(*args, **kwargs)
        self.client_error_patcher = mock.patch.object(
            self.storage._client.connection_pool,
            'get_connection',
            side_effect=redis.RedisError('connection error'))

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
                self.storage.get_all(**self.storage_kw)  # not raising


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

    def test_number_of_fetched_records_can_be_limited_in_settings(self):
        for i in range(4):
            self.create_record({'phone': 'tel-%s' % i})

        results, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(len(results), 4)

        settings = self.settings.copy()
        settings['cliquet.storage_max_fetch_size'] = 2
        config = self._get_config(settings=settings)
        limited = self.backend.load_from_config(config)

        results, count = limited.get_all(**self.storage_kw)
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
        msg = 'Pool size 1 ignored for PostgreSQL backend (Already set to 10).'
        with mock.patch('cliquet.storage.postgresql.warnings.warn') as mocked:
            self.backend.load_from_config(self._get_config(settings=settings))
            mocked.assert_any_call(msg)
