import time

import mock
from pyramid import testing
from kinto.core import utils
from kinto.core.testing import skip_if_travis, DummyRequest, ThreadMixin
from kinto.core.storage import exceptions, Filter, Sort, heartbeat


RECORD_ID = '472be9ec-26fe-461b-8282-9c4e4b207ab3'


class BaseTestStorage:
    backend = None

    settings = {}

    def setUp(self):
        super().setUp()
        self.storage = self.backend.load_from_config(self._get_config())
        self.storage.initialize_schema()
        self.id_field = 'id'
        self.modified_field = 'last_modified'
        self.client_error_patcher = None

        self.record = {'foo': 'bar'}
        self.storage_kw = {
            'collection_id': 'test',
            'parent_id': '1234',
            'auth': 'Basic bWF0OjI='
        }
        self.other_parent_id = '5678'
        self.other_auth = 'Basic bWF0OjE='

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
        super().tearDown()
        self.storage.flush()

    def create_record(self, record=None, id_generator=None, **kwargs):
        record = record or self.record
        kw = {**self.storage_kw, **kwargs}
        return self.storage.create(record=record,
                                   id_generator=id_generator,
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
            (self.storage.purge_deleted, {}),
            (self.storage.get_all, {}),
        ]
        for call, kwargs in calls:
            kwargs.update(**self.storage_kw)
            self.assertRaises(exceptions.BackendError, call, **kwargs)
        self.assertRaises(exceptions.BackendError,
                          self.storage.flush,
                          auth=self.other_auth)

    def test_initialize_schema_is_idempotent(self):
        self.storage.initialize_schema()
        self.storage.initialize_schema()  # not raising.

    def test_ping_returns_false_if_unavailable(self):
        request = DummyRequest()
        request.headers['Authorization'] = self.storage_kw['auth']
        request.registry.settings = {'readonly': 'false'}
        ping = heartbeat(self.storage)

        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.7):
            ping(request)

        self.client_error_patcher.start()
        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.7):
            self.assertFalse(ping(request))
        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.5):
            self.assertFalse(ping(request))

    def test_ping_returns_true_when_working(self):
        request = DummyRequest()
        request.headers['Authorization'] = 'Basic bWF0OjI='
        ping = heartbeat(self.storage)
        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.7):
            self.assertTrue(ping(request))
        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.5):
            self.assertTrue(ping(request))

    def test_ping_returns_true_when_working_in_readonly_mode(self):
        request = DummyRequest()
        request.headers['Authorization'] = 'Basic bWF0OjI='
        request.registry.settings = {'readonly': 'true'}
        ping = heartbeat(self.storage)
        self.assertTrue(ping(request))

    def test_ping_returns_false_if_unavailable_in_readonly_mode(self):
        request = DummyRequest()
        request.headers['Authorization'] = 'Basic bWF0OjI='
        request.registry.settings = {'readonly': 'true'}
        ping = heartbeat(self.storage)
        with mock.patch.object(self.storage, 'get_all',
                               side_effect=exceptions.BackendError("Boom!")):
            self.assertFalse(ping(request))

    def test_ping_logs_error_if_unavailable(self):
        request = DummyRequest()
        self.client_error_patcher.start()
        ping = heartbeat(self.storage)

        with mock.patch('kinto.core.storage.logger.exception') as exc_handler:
            self.assertFalse(ping(request))

        self.assertTrue(exc_handler.called)

    def test_ping_leaves_no_tombstone(self):
        request = DummyRequest()
        request.headers['Authorization'] = 'Basic bWF0OjI='
        ping = heartbeat(self.storage)
        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.7):
            ping(request)
        with mock.patch('kinto.core.storage.random.SystemRandom.random', return_value=0.5):
            ping(request)
        records, count = self.storage.get_all(parent_id='__heartbeat__',
                                              collection_id='__heartbeat__',
                                              include_deleted=True)
        self.assertEqual(len(records), 0)

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

    def test_create_supports_unicode_for_parent_and_id(self):
        unicode_id = 'Rémy'
        self.create_record(parent_id=unicode_id, collection_id=unicode_id)

    def test_create_does_not_overwrite_the_provided_id(self):
        record = {**self.record, self.id_field: RECORD_ID}
        stored = self.create_record(record=record)
        self.assertEqual(stored[self.id_field], RECORD_ID)

    def test_create_raise_unicity_error_if_provided_id_exists(self):
        record = {**self.record, self.id_field: RECORD_ID}
        self.create_record(record=record)
        record = {**self.record, self.id_field: RECORD_ID}
        self.assertRaises(exceptions.UnicityError,
                          self.create_record,
                          record=record)

    def test_create_does_not_raise_unicity_error_if_ignore_conflict_is_set(self):
        record = {**self.record, self.id_field: RECORD_ID}
        self.create_record(record=record, ignore_conflict=True)
        record = {**self.record, self.id_field: RECORD_ID}
        self.create_record(record=record, ignore_conflict=True)  # not raising

    def test_create_keep_existing_if_ignore_conflict_is_set(self):
        record = {**self.record, "synced": True, self.id_field: RECORD_ID}
        self.create_record(record=record)
        new_record = {**self.record, self.id_field: RECORD_ID}
        result = self.create_record(record=new_record, ignore_conflict=True)
        assert 'synced' in result

    def test_create_does_generate_a_new_last_modified_field(self):
        record = {**self.record}
        self.assertNotIn(self.modified_field, record)
        created = self.create_record(record=record)
        self.assertIn(self.modified_field, created)

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

    def test_update_generates_a_new_last_modified_field_if_not_present(self):
        stored = self.create_record()
        record_id = stored[self.id_field]
        self.assertNotIn(self.modified_field, self.record)
        self.storage.update(object_id=record_id, record=self.record,
                            **self.storage_kw)
        retrieved = self.storage.get(object_id=record_id, **self.storage_kw)
        self.assertIn(self.modified_field, retrieved)
        self.assertGreater(retrieved[self.modified_field],
                           stored[self.modified_field])

    def test_delete_works_properly(self):
        stored = self.create_record()
        self.storage.delete(object_id=stored['id'], **self.storage_kw)
        self.assertRaises(  # Shouldn't exist.
            exceptions.RecordNotFoundError,
            self.storage.get,
            object_id=stored['id'],
            **self.storage_kw
        )

    def test_delete_works_even_on_second_time(self):
        # Create a record
        self.storage.create('test', '1234', {"id": "demo"})
        # Delete the record
        self.storage.delete('test', '1234', "demo", with_deleted=True)
        # Update a record (it recreates it.)
        self.storage.update('test', '1234', "demo", {"id": "demo"})
        # Delete the record without errors
        self.storage.delete('test', '1234', "demo", with_deleted=True)

    def test_delete_can_specify_the_last_modified(self):
        stored = self.create_record()
        last_modified = stored[self.modified_field] + 10
        self.storage.delete(
            object_id=stored['id'],
            last_modified=last_modified,
            **self.storage_kw)

        records, count = self.storage.get_all(
            include_deleted=True, **self.storage_kw)
        self.assertEquals(records[0][self.modified_field], last_modified)

    def test_delete_raise_when_unknown(self):
        self.assertRaises(
            exceptions.RecordNotFoundError,
            self.storage.delete,
            object_id=RECORD_ID,
            **self.storage_kw
        )

    def test_get_all_handles_parent_id_pattern_matching(self):
        self.create_record(parent_id='abc', collection_id='c')
        record = self.create_record(parent_id='abc', collection_id='c')
        self.storage.delete(object_id=record['id'], parent_id='abc', collection_id='c')
        self.create_record(parent_id='efg', collection_id='c')

        records, total_records = self.storage.get_all(parent_id='ab*', collection_id='c',
                                                      include_deleted=True)
        self.assertEquals(len(records), 2)
        self.assertEquals(total_records, 1)

    def test_get_all_does_proper_parent_id_pattern_matching(self):
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='xabcx', collection_id='c')
        self.create_record(parent_id='efg', collection_id='c')

        records, total_records = self.storage.get_all(parent_id='ab*', collection_id='c',
                                                      include_deleted=True)
        self.assertEquals(len(records), 1)
        self.assertEquals(len(records), total_records)

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

    def test_get_all_handle_sorting_on_subobject(self):
        for x in range(10):
            record = dict(**self.record)
            record["person"] = dict(age=x)
            self.create_record(record)
        sorting = [Sort('person.age', 1)]
        records, _ = self.storage.get_all(sorting=sorting,
                                          **self.storage_kw)
        self.assertLess(records[0]['person']['age'],
                        records[-1]['person']['age'])

    def test_get_all_sorting_is_consistent_with_filtering(self):
        self.create_record({'flavor': 'strawberry'})
        self.create_record({'flavor': 'blueberry', 'author': None})
        self.create_record({'flavor': 'raspberry', 'author': 1})
        self.create_record({'flavor': 'orange', 'author': True})
        self.create_record({'flavor': 'watermelon', 'author': 'Ethan'})
        sorting = [Sort('author', 1)]
        records, _ = self.storage.get_all(sorting=sorting, **self.storage_kw)
        # Some interesting values to compare against
        values = ['A', 'Z', '', 0, 4]

        for value in values:
            # Together, these filters should provide the entire list
            filter_less = Filter('author', value, utils.COMPARISON.LT)
            filter_min = Filter('author', value, utils.COMPARISON.MIN)
            smaller_records, _ = self.storage.get_all(filters=[filter_less],
                                                      sorting=sorting,
                                                      **self.storage_kw)
            greater_records, _ = self.storage.get_all(filters=[filter_min],
                                                      sorting=sorting,
                                                      **self.storage_kw)
            other_records = smaller_records + greater_records
            self.assertEqual(records, other_records,
                             "Filtering is not consistent with sorting when filtering "
                             "using value {}: {} (LT) + {} (MIN) != {}".format(
                                 value, smaller_records, greater_records, records))

        # Same test but with MAX and GT
        for value in values:
            # Together, these filters should provide the entire list
            filter_less = Filter('author', value, utils.COMPARISON.MAX)
            filter_min = Filter('author', value, utils.COMPARISON.GT)
            smaller_records, _ = self.storage.get_all(filters=[filter_less],
                                                      sorting=sorting,
                                                      **self.storage_kw)
            greater_records, _ = self.storage.get_all(filters=[filter_min],
                                                      sorting=sorting,
                                                      **self.storage_kw)
            other_records = smaller_records + greater_records
            self.assertEqual(records, other_records,
                             "Filtering is not consistent with sorting when filtering "
                             "using value {}: {} (MAX) + {} (GT) != {}".format(
                                 value, smaller_records, greater_records, records))

    def test_get_all_can_filter_with_list_of_values(self):
        for l in ['a', 'b', 'c']:
            self.create_record({'code': l})
        filters = [Filter('code', ['a', 'b'], utils.COMPARISON.IN)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 2)

    def test_get_all_can_filter_with_numeric_values(self):
        self.create_record({'missing': 'code'})
        for l in [1, 10, 6, 46]:
            self.create_record({'code': l})

        sorting = [Sort('code', 1)]
        filters = [Filter('code', 10, utils.COMPARISON.MAX)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          **self.storage_kw)
        self.assertEqual(records[0]['code'], 1)
        self.assertEqual(records[1]['code'], 6)
        self.assertEqual(records[2]['code'], 10)
        self.assertEqual(len(records), 3)

        filters = [Filter('code', 10, utils.COMPARISON.LT)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          **self.storage_kw)
        self.assertEqual(records[0]['code'], 1)
        self.assertEqual(records[1]['code'], 6)
        self.assertEqual(len(records), 2)

    def test_get_all_can_filter_with_numeric_id(self):
        for l in [0, 42]:
            self.create_record({'id': str(l)})

        filters = [Filter('id', 0, utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

        filters = [Filter('id', 42, utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

    def test_get_all_can_filter_with_numeric_strings(self):
        for l in ["0566199093", "0781566199"]:
            self.create_record({'phone': l})
        filters = [Filter('phone', "0566199093", utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

    def test_get_all_can_filter_with_empty_numeric_strings(self):
        for l in ["0566199093", "0781566199"]:
            self.create_record({'phone': l})
        filters = [Filter('phone', "", utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 0)

    def test_get_all_can_filter_with_float_values(self):
        for l in [10, 11.5, 8.5, 6, 7.5]:
            self.create_record({'note': l})
        filters = [Filter('note', 9.5, utils.COMPARISON.LT)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 3)

    def test_get_all_can_filter_with_strings(self):
        for l in ["Rémy", "Alexis", "Marie"]:
            self.create_record({'name': l})
        sorting = [Sort('name', 1)]
        filters = [Filter('name', "Mathieu", utils.COMPARISON.LT)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          **self.storage_kw)
        self.assertEqual(records[0]['name'], "Alexis")
        self.assertEqual(records[1]['name'], "Marie")
        self.assertEqual(len(records), 2)

    def test_get_all_can_filter_minimum_value_with_strings(self):
        for v in ["49.0", "6.0", "53.0b4"]:
            self.create_record({"product": {"version": v}})
        sorting = [Sort("product.version", 1)]
        filters = [Filter("product.version", "50.0", utils.COMPARISON.MIN)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          **self.storage_kw)
        self.assertEqual(records[0]["product"]["version"], "53.0b4")
        self.assertEqual(records[1]["product"]["version"], "6.0")
        self.assertEqual(len(records), 2)

    def test_get_all_does_not_implicitly_cast(self):
        for v in ["49.0", "6.0", "53.0b4"]:
            self.create_record({"product": {"version": v}})
        sorting = [Sort("product.version", 1)]
        filters = [Filter("product.version", 50.0, utils.COMPARISON.MIN)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 0)  # 50 (number) > strings

    def test_get_all_can_deal_with_none_values(self):
        self.create_record({"name": "Alexis"})
        self.create_record({"title": "haha"})
        self.create_record({"name": "Mathieu"})
        filters = [Filter("name", "Fanny", utils.COMPARISON.GT)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        # NULLs compare as greater than everything
        self.assertEqual(len(records), 2)
        # But we aren't clear on what the order will be
        mathieu_record = records[0] if 'name' in records[0] else records[1]
        haha_record = records[1] if 'name' in records[0] else records[0]
        self.assertEqual(mathieu_record["name"], "Mathieu")
        self.assertEqual(haha_record["title"], "haha")

        filters = [Filter("name", "Fanny", utils.COMPARISON.LT)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "Alexis")

    def test_get_all_can_filter_with_none_values(self):
        self.create_record({"name": "Alexis", "salary": None})
        self.create_record({"name": "Mathieu", "salary": "null"})
        self.create_record({"name": "Niko", "salary": ""})
        self.create_record({"name": "Ethan"})   # missing salary
        filters = [Filter("salary", None, utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "Alexis")

    def test_get_all_can_filter_with_list_of_values_on_id(self):
        record1 = self.create_record({'code': 'a'})
        record2 = self.create_record({'code': 'b'})
        filters = [Filter('id', [record1['id'], record2['id']],
                          utils.COMPARISON.IN)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 2)

    def test_get_all_returns_empty_when_including_list_of_empty_values(self):
        self.create_record({'code': 'a'})
        self.create_record({'code': 'b'})
        filters = [Filter('id', [], utils.COMPARISON.IN)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 0)

    def test_get_all_can_filter_with_list_of_excluded_values(self):
        for l in ['a', 'b', 'c']:
            self.create_record({'code': l})
        filters = [Filter('code', ('a', 'b'), utils.COMPARISON.EXCLUDE)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

    def test_get_all_can_filter_a_list_of_integer_values(self):
        for l in [1, 2, 3]:
            self.create_record({'code': l})
        filters = [Filter('code', (1, 2), utils.COMPARISON.EXCLUDE)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

    def test_get_all_can_filter_a_list_of_mixed_typed_values(self):
        for l in [1, 2, 3]:
            self.create_record({'code': l})
        filters = [Filter('code', (1, "b"), utils.COMPARISON.EXCLUDE)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 2)

    def test_get_all_can_filter_a_list_of_integer_values_on_subobjects(self):
        for l in [1, 2, 3]:
            self.create_record({'code': {'city': l}})
        filters = [Filter('code.city', (1, 2), utils.COMPARISON.EXCLUDE)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

    def test_get_all_can_filter_matching_a_list(self):
        self.create_record({"flavor": "strawberry", "orders": []})
        self.create_record({"flavor": "blueberry", "orders": [1]})
        self.create_record({"flavor": "pineapple", "orders": [1, 2]})
        self.create_record({"flavor": "watermelon", "orders": ""})
        self.create_record({"flavor": "raspberry", "orders": {}})
        filters = [Filter("orders", [], utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["flavor"], "strawberry")

        filters = [Filter("orders", [1], utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["flavor"], "blueberry")

    def test_get_all_can_filter_matching_an_object(self):
        self.create_record({"flavor": "strawberry", "attributes": {}})
        self.create_record({
            "flavor": "blueberry",
            "attributes": {"ibu": 25, "seen_on": "2017-06-01"},
        })
        self.create_record({
            "flavor": "watermelon",
            "attributes": {"ibu": 25, "seen_on": "2017-06-01", "price": 9.99},
        })
        self.create_record({"flavor": "raspberry", "attributes": []})
        filters = [Filter("attributes", {}, utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["flavor"], "strawberry")

        filters = [Filter("attributes", {"ibu": 25, "seen_on": "2017-06-01"}, utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["flavor"], "blueberry")

    def test_get_all_supports_has(self):
        self.create_record({"flavor": "strawberry"})
        self.create_record({"flavor": "blueberry", "author": None})
        self.create_record({"flavor": "raspberry", "author": ""})
        self.create_record({"flavor": "watermelon", "author": "hello"})
        self.create_record({"flavor": "pineapple", "author": "null"})
        filters = [Filter("author", True, utils.COMPARISON.HAS)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 4)
        self.assertEqual(sorted([r['flavor'] for r in records]),
                         ["blueberry", "pineapple", "raspberry", "watermelon"])

        filters = [Filter("author", False, utils.COMPARISON.HAS)]
        records, _ = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["flavor"], "strawberry")

    def test_get_all_can_filter_by_subobjects_values(self):
        for l in ['a', 'b', 'c']:
            self.create_record({'code': {'sub': l}})
        filters = [Filter('code.sub', 'a', utils.COMPARISON.EQ)]
        records, _ = self.storage.get_all(filters=filters,
                                          **self.storage_kw)
        self.assertEqual(len(records), 1)

    def test_get_all_can_filter_with_like_and_implicit_wildchars(self):
        self.create_record({'name': 'foo'})
        self.create_record({'name': 'aafooll'})
        self.create_record({'name': 'bar'})
        self.create_record({'name': 'FOOBAR'})

        filters = [Filter('name', 'FoO', utils.COMPARISON.LIKE)]
        results, count = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(results), 3)

    def test_get_all_can_filter_with_wildchars(self):
        self.create_record({'name': 'eabcg'})
        self.create_record({'name': 'aabcc'})
        self.create_record({'name': 'abc'})
        self.create_record({'name': 'aec'})
        self.create_record({'name': 'efg'})

        filters = [Filter('name', 'a*b*c', utils.COMPARISON.LIKE)]
        results, count = self.storage.get_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(results), 2)


class TimestampsTest:
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
    def test_timestamps_are_unique(self):  # pragma: no cover
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

    def test_the_timestamp_is_not_updated_when_collection_remains_empty(self):
        # Get timestamp once.
        first = self.storage.collection_timestamp(**self.storage_kw)

        time.sleep(0.002)  # wait some time.

        # Check that second time returns the same value.
        second = self.storage.collection_timestamp(**self.storage_kw)
        self.assertEqual(first, second)

    def test_the_timestamp_are_based_on_real_time_milliseconds(self):
        before = utils.msec_time()
        time.sleep(0.002)  # 2 msec
        record = self.create_record()
        now = record['last_modified']
        time.sleep(0.002)  # 2 msec
        after = utils.msec_time()
        self.assertTrue(before < now < after,
                        '{} < {} < {}'.format(before, now, after))

    def test_timestamp_are_always_incremented_above_existing_value(self):
        # Create a record with normal clock
        record = self.create_record()
        current = record['last_modified']

        # Patch the clock to return a time in the past, before the big bang
        with mock.patch('kinto.core.utils.msec_time') as time_mocked:
            time_mocked.return_value = -1

            record = self.create_record()
            after = record['last_modified']

        # Expect the last one to be based on the highest value
        self.assertTrue(0 < current < after,
                        '0 < {} < {}'.format(current, after))

    def test_create_uses_specified_last_modified_if_collection_empty(self):
        # Collection is empty, create a new record with a specified timestamp.
        last_modified = 1448881675541
        record = {**self.record, self.id_field: RECORD_ID, self.modified_field: last_modified}
        self.create_record(record=record)

        # Check that the record was assigned the specified timestamp.
        retrieved = self.storage.get(object_id=RECORD_ID, **self.storage_kw)
        self.assertEquals(retrieved[self.modified_field], last_modified)

        # Collection timestamp is now the same as its only record.
        collection_ts = self.storage.collection_timestamp(**self.storage_kw)
        self.assertEquals(collection_ts, last_modified)

    def test_create_ignores_specified_last_modified_if_in_the_past(self):
        # Create a first record, and get the timestamp.
        first_record = self.create_record()
        timestamp_before = first_record[self.modified_field]

        # Create a new record with its timestamp in the past.
        record = {**self.record,
                  self.id_field: RECORD_ID,
                  self.modified_field: timestamp_before - 10}
        self.create_record(record=record)

        # Check that record timestamp is the one specified.
        retrieved = self.storage.get(object_id=RECORD_ID, **self.storage_kw)
        self.assertLess(retrieved[self.modified_field], timestamp_before)
        self.assertEquals(retrieved[self.modified_field],
                          record[self.modified_field])

        # Check that collection timestamp was bumped (change happened).
        timestamp = self.storage.collection_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)

    def test_create_ignores_specified_last_modified_if_equal(self):
        # Create a first record, and get the timestamp.
        first_record = self.create_record()
        timestamp_before = first_record[self.modified_field]

        # Create a new record with its timestamp in the past.
        record = {**self.record,
                  self.id_field: RECORD_ID,
                  self.modified_field: timestamp_before}
        self.create_record(record=record)

        # Check that record timestamp is the one specified.
        retrieved = self.storage.get(object_id=RECORD_ID, **self.storage_kw)
        self.assertGreater(retrieved[self.modified_field], timestamp_before)
        self.assertGreater(retrieved[self.modified_field],
                           record[self.modified_field])

        # Check that collection timestamp was bumped (change happened).
        timestamp = self.storage.collection_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)

    def test_update_uses_specified_last_modified_if_in_future(self):
        stored = self.create_record()
        record_id = stored[self.id_field]
        timestamp_before = stored[self.modified_field]

        # Set timestamp manually in the future.
        stored[self.modified_field] = timestamp_before + 10
        self.storage.update(object_id=record_id, record=stored,
                            **self.storage_kw)

        # Check that record timestamp is the one specified.
        retrieved = self.storage.get(object_id=record_id, **self.storage_kw)
        self.assertGreater(retrieved[self.modified_field], timestamp_before)
        self.assertGreaterEqual(retrieved[self.modified_field],
                                stored[self.modified_field])

        # Check that collection timestamp took the one specified (in future).
        timestamp = self.storage.collection_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)
        self.assertEquals(timestamp, retrieved[self.modified_field])

    def test_update_ignores_specified_last_modified_if_in_the_past(self):
        stored = self.create_record()
        record_id = stored[self.id_field]
        timestamp_before = stored[self.modified_field]

        # Set timestamp manually in the future.
        stored[self.modified_field] = timestamp_before - 10
        self.storage.update(object_id=record_id, record=stored,
                            **self.storage_kw)

        # Check that record timestamp is the one specified.
        retrieved = self.storage.get(object_id=record_id, **self.storage_kw)
        self.assertLess(retrieved[self.modified_field], timestamp_before)
        self.assertEquals(retrieved[self.modified_field],
                          stored[self.modified_field])

        # Check that collection timestamp was bumped (change happened).
        timestamp = self.storage.collection_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)

    def test_update_ignores_specified_last_modified_if_equal(self):
        stored = self.create_record()
        record_id = stored[self.id_field]
        timestamp_before = stored[self.modified_field]

        # Do not change the timestamp.
        self.storage.update(object_id=record_id, record=stored,
                            **self.storage_kw)

        # Check that record timestamp was bumped.
        retrieved = self.storage.get(object_id=record_id, **self.storage_kw)
        self.assertGreater(retrieved[self.modified_field], timestamp_before)
        self.assertGreater(retrieved[self.modified_field],
                           stored[self.modified_field])

        # Check that collection timestamp was bumped (change happened).
        timestamp = self.storage.collection_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)


class DeletedRecordsTest:
    def _get_last_modified_filters(self):
        start = self.storage.collection_timestamp(**self.storage_kw)
        time.sleep(0.1)
        return [
            Filter(self.modified_field, start, utils.COMPARISON.GT)
        ]

    def create_and_delete_record(self, record=None):
        """Helper to create and delete a record."""
        record = record or {'challenge': 'accepted'}
        record = self.create_record(record)
        time.sleep(0.001)  # 1 msec
        deleted = self.storage.delete(object_id=record['id'],
                                      **self.storage_kw)
        time.sleep(0.001)  # 1 msec
        return deleted

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

    def test_recreating_a_deleted_record_should_delete_its_tombstone(self):
        record = {'id': 'jesus', 'rebirth': True}
        self.create_and_delete_record(record)
        self.create_record(record)
        records, count = self.storage.get_all(include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(count, 1)  # One existing.
        self.assertEqual(len(records), 1)  # No tombstone.

    def test_deleting_a_record_twice_should_update_its_tombstone(self):
        record = {'id': 'jesus', 'rebirth': True}
        deleted = self.create_and_delete_record(record)
        before = deleted['last_modified']
        deleted = self.create_and_delete_record(record)
        after = deleted['last_modified']
        self.assertNotEqual(before, after)

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
        record = {'challenge': 'accepted'}
        record = self.create_record(record)
        self.storage.delete_all(**self.storage_kw)
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 1)
        self.assertEqual(count, 0)

    def test_delete_all_can_delete_without_deleted_items(self):
        filters = self._get_last_modified_filters()
        record = {'challenge': 'accepted'}
        record = self.create_record(record)
        self.storage.delete_all(with_deleted=False, **self.storage_kw)
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 0)
        self.assertEqual(count, 0)

    def test_delete_can_delete_without_deleted_items(self):
        filters = self._get_last_modified_filters()
        record = {'challenge': 'accepted'}
        record = self.create_record(record)
        self.storage.delete(object_id=record['id'], with_deleted=False,
                            **self.storage_kw)
        records, count = self.storage.get_all(filters=filters,
                                              include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(len(records), 0)
        self.assertEqual(count, 0)

    def test_delete_all_deletes_records(self):
        self.create_record()
        self.create_record()
        self.storage.delete_all(**self.storage_kw)
        _, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(count, 0)

    def test_delete_all_can_delete_by_parent_id(self):
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='efg', collection_id='c')
        self.storage.delete_all(parent_id='ab*',
                                collection_id=None,
                                with_deleted=False)
        records, count = self.storage.get_all(parent_id='abc',
                                              collection_id='c',
                                              include_deleted=True)
        self.assertEqual(count, 0)
        self.assertEqual(len(records), 0)
        records, count = self.storage.get_all(parent_id='efg',
                                              collection_id='c',
                                              include_deleted=True)
        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)

    def test_delete_all_does_proper_parent_id_matching(self):
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='xabcx', collection_id='c')
        self.create_record(parent_id='efg', collection_id='c')
        self.storage.delete_all(parent_id='ab*',
                                collection_id=None,
                                with_deleted=False)
        records, count = self.storage.get_all(parent_id='xabcx',
                                              collection_id='c',
                                              include_deleted=True)
        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)
        records, count = self.storage.get_all(parent_id='efg',
                                              collection_id='c',
                                              include_deleted=True)
        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)

    def test_delete_all_does_proper_matching(self):
        self.create_record(parent_id='abc', collection_id='c', record={"id": "id1"})
        self.create_record(parent_id='def', collection_id='g', record={"id": "id1"})
        self.storage.delete_all(parent_id='ab*',
                                collection_id=None,
                                with_deleted=False)
        records, count = self.storage.get_all(parent_id='def',
                                              collection_id='g',
                                              include_deleted=True)
        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)

    def test_delete_all_can_delete_by_parent_id_with_tombstones(self):
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='efg', collection_id='c')
        self.storage.delete_all(parent_id='ab*',
                                collection_id=None,
                                with_deleted=True)
        records, count = self.storage.get_all(parent_id='efg',
                                              collection_id='c',
                                              include_deleted=True)
        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)

        records, count = self.storage.get_all(parent_id='abc',
                                              collection_id='c',
                                              include_deleted=True)
        self.assertEqual(count, 0)
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0]['deleted'])
        self.assertTrue(records[1]['deleted'])

    def test_delete_all_can_delete_partially(self):
        self.create_record({'foo': 'po'})
        self.create_record()
        filters = [Filter('foo', 'bar', utils.COMPARISON.EQ)]
        self.storage.delete_all(filters=filters, **self.storage_kw)
        _, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(count, 1)

    def test_delete_all_supports_limit(self):
        self.create_record()
        self.create_record()
        self.storage.delete_all(limit=1, **self.storage_kw)
        _, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(count, 1)

    def test_delete_all_supports_sorting(self):
        for i in range(5):
            self.create_record({'foo': i})
        sorting = [Sort('foo', -1)]
        self.storage.delete_all(limit=2, sorting=sorting, **self.storage_kw)
        records, count = self.storage.get_all(sorting=sorting, **self.storage_kw)
        self.assertEqual(count, 3)
        self.assertEqual(records[0]['foo'], 2)

    def test_purge_deleted_remove_all_tombstones(self):
        self.create_record()
        self.create_record()
        self.storage.delete_all(**self.storage_kw)
        num_removed = self.storage.purge_deleted(**self.storage_kw)
        self.assertEqual(num_removed, 2)
        records, count = self.storage.get_all(include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(count, 0)
        self.assertEqual(len(records), 0)

    def test_purge_deleted_remove_all_tombstones_by_parent_id(self):
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='abc', collection_id='c')
        self.create_record(parent_id='efg', collection_id='c')
        self.storage.delete_all(parent_id='abc', collection_id='c')
        self.storage.delete_all(parent_id='efg', collection_id='c')
        num_removed = self.storage.purge_deleted(parent_id='ab*',
                                                 collection_id=None)
        self.assertEqual(num_removed, 2)

    def test_purge_deleted_removes_timestamps_by_parent_id(self):
        self.create_record(parent_id='/abc/a', collection_id='c')
        self.create_record(parent_id='/abc/a', collection_id='c')
        self.create_record(parent_id='/efg', collection_id='c')

        before1 = self.storage.collection_timestamp(parent_id='/abc/a', collection_id='c')
        # Different parent_id with record.
        before2 = self.storage.collection_timestamp(parent_id='/efg', collection_id='c')
        # Different parent_id without record.
        before3 = self.storage.collection_timestamp(parent_id='/ijk', collection_id='c')

        self.storage.delete_all(parent_id='/abc/*', collection_id=None, with_deleted=False)
        self.storage.purge_deleted(parent_id='/abc/*', collection_id=None)

        after1 = self.storage.collection_timestamp(parent_id='/abc/a', collection_id='c')
        after2 = self.storage.collection_timestamp(parent_id='/efg', collection_id='c')
        after3 = self.storage.collection_timestamp(parent_id='/ijk', collection_id='c')

        self.assertNotEqual(before1, after1)
        self.assertEqual(before2, after2)
        self.assertEqual(before3, after3)

    def test_purge_deleted_works_when_no_tombstones(self):
        num_removed = self.storage.purge_deleted(**self.storage_kw)
        self.assertEqual(num_removed, 0)

    def test_purge_deleted_remove_with_before_remove_olders_exclusive(self):
        older = self.create_record()
        newer = self.create_record()
        self.storage.delete(object_id=older['id'], **self.storage_kw)
        self.storage.delete(object_id=newer['id'], **self.storage_kw)
        records, count = self.storage.get_all(include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(count, 0)
        self.assertEqual(len(records), 2)
        num_removed = self.storage.purge_deleted(
            before=max([r['last_modified'] for r in records]),
            **self.storage_kw)
        self.assertEqual(num_removed, 1)
        records, count = self.storage.get_all(include_deleted=True,
                                              **self.storage_kw)
        self.assertEqual(count, 0)
        self.assertEqual(len(records), 1)

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

    def test_sorting_on_numeric_arbitrary_field(self):
        filters = self._get_last_modified_filters()
        for l in [1, 10, 6, 46]:
            self.create_record({'status': l})

        sorting = [Sort('status', -1)]
        records, _ = self.storage.get_all(sorting=sorting, filters=filters,
                                          include_deleted=True,
                                          **self.storage_kw)
        self.assertEqual(records[0]['status'], 46)
        self.assertEqual(records[1]['status'], 10)
        self.assertEqual(records[2]['status'], 6)
        self.assertEqual(records[3]['status'], 1)

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
        self.assertEqual(count, 1)
        self.assertNotIn('deleted', records[0])
        self.assertEqual(len(records), 1)

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

    def test_delete_all_supports_pagination_rules(self):
        for i in range(6):
            self.create_record({'foo': i})

        pagination_rules = [[Filter('foo', 3, utils.COMPARISON.GT)]]
        deleted = self.storage.delete_all(limit=4, pagination_rules=pagination_rules,
                                          **self.storage_kw)
        self.assertEqual(len(deleted), 2)


class ParentRecordAccessTest:
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
        kw = {**self.storage_kw,
              'parent_id': self.other_parent_id,
              'auth': self.other_auth}
        self.storage.update(object_id=record['id'], record=new_record, **kw)

        not_updated = self.storage.get(object_id=record['id'],
                                       **self.storage_kw)
        self.assertNotIn("another", not_updated)

    def test_create_bytes_value_gets_back_str(self):
        data = {'steak': 'haché'.encode(encoding='utf-8')}
        self.assertIsInstance(data['steak'], bytes)

        record = self.create_record(data)

        back_record = self.storage.get(object_id=record['id'],
                                       **self.storage_kw)
        self.assertIsInstance(back_record['steak'], str)
        self.assertEqual(back_record['steak'], 'haché')

    def test_create_bytes_value_bad_encoding_raises(self):
        self.assertRaises(OverflowError,
                          self.create_record,
                          {'steak': 'haché'.encode(encoding='iso-8859-1')}
                          )

    def test_update_bytes_value_gets_back_str(self):
        record = self.create_record()

        new_record = {'steak': 'haché'.encode(encoding='utf-8')}
        self.assertIsInstance(new_record['steak'], bytes)

        self.storage.update(object_id=record['id'],
                            record=new_record,
                            **self.storage_kw)

        back_record = self.storage.get(object_id=record['id'],
                                       **self.storage_kw)
        self.assertIsInstance(back_record['steak'], str)
        self.assertEqual(back_record['steak'], 'haché')

    def test_update_bytes_value_bad_encoding_raises(self):
        record = self.create_record()

        new_record = {'steak': 'haché'.encode(encoding='iso-8859-1')}
        self.assertRaises(OverflowError,
                          self.storage.update,
                          object_id=record['id'],
                          record=new_record,
                          **self.storage_kw
                          )


class StorageTest(ThreadMixin,
                  TimestampsTest,
                  DeletedRecordsTest,
                  ParentRecordAccessTest,
                  BaseTestStorage):
    """Compound of all storage tests."""
    pass
