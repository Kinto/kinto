import time
from unittest import mock

from pyramid import testing

from kinto.core import utils
from kinto.core.storage import MISSING, Filter, Sort, exceptions, heartbeat
from kinto.core.testing import DummyRequest, ThreadMixin, skip_if_ci

OBJECT_ID = "472be9ec-26fe-461b-8282-9c4e4b207ab3"


class BaseTestStorage:
    backend = None

    settings = {}

    def setUp(self):
        super().setUp()
        self.storage = self.backend.load_from_config(self._get_config())
        self.storage.initialize_schema()
        self.id_field = "id"
        self.modified_field = "last_modified"
        self.client_error_patcher = None

        self.obj = {"foo": "bar"}
        self.storage_kw = {"resource_name": "test", "parent_id": "1234"}
        self.other_parent_id = "5678"
        self.auth = "Basic bWF0OjE="

    def _get_config(self, settings=None):
        """Mock Pyramid config object."""
        if settings is None:
            settings = self.settings
        config = testing.setUp()
        config.add_settings(settings)
        return config

    def tearDown(self):
        mock.patch.stopall()
        super().tearDown()
        self.storage.flush()

    def create_object(self, obj=None, id_generator=None, **kwargs):
        obj = obj or self.obj
        kw = {**self.storage_kw, **kwargs}
        return self.storage.create(obj=obj, id_generator=id_generator, **kw)

    def test_raises_backend_error_if_error_occurs_on_client(self):
        self.client_error_patcher.start()
        self.assertRaises(exceptions.BackendError, self.storage.list_all, **self.storage_kw)
        self.assertRaises(exceptions.BackendError, self.storage.count_all, **self.storage_kw)

    def test_backend_error_provides_original_exception(self):
        self.client_error_patcher.start()
        try:
            self.storage.list_all(**self.storage_kw)
        except exceptions.BackendError as e:
            error = e
        self.assertTrue(isinstance(error.original, Exception))

    def test_backend_error_is_raised_anywhere(self):
        self.client_error_patcher.start()
        calls = [
            (self.storage.resource_timestamp, {}),
            (self.storage.create, dict(obj={})),
            (self.storage.get, dict(object_id={})),
            (self.storage.update, dict(object_id="", obj={})),
            (self.storage.delete, dict(object_id="")),
            (self.storage.delete_all, {}),
            (self.storage.purge_deleted, {}),
            (self.storage.list_all, {}),
            (self.storage.count_all, {}),
        ]
        for call, kwargs in calls:
            kwargs.update(**self.storage_kw)
            self.assertRaises(exceptions.BackendError, call, **kwargs)
        self.assertRaises(exceptions.BackendError, self.storage.flush)

    def test_initialize_schema_is_idempotent(self):
        self.storage.initialize_schema()
        self.storage.initialize_schema()  # not raising.

    def test_ping_returns_false_if_unavailable(self):
        request = DummyRequest()
        request.headers["Authorization"] = self.auth
        request.registry.settings = {"readonly": "false"}
        ping = heartbeat(self.storage)

        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.7):
            ping(request)

        self.client_error_patcher.start()
        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.7):
            self.assertFalse(ping(request))
        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.5):
            self.assertFalse(ping(request))

    def test_ping_returns_true_when_working(self):
        request = DummyRequest()
        request.headers["Authorization"] = self.auth
        ping = heartbeat(self.storage)
        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.7):
            self.assertTrue(ping(request))
        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.5):
            self.assertTrue(ping(request))

    def test_ping_returns_true_when_working_in_readonly_mode(self):
        request = DummyRequest()
        request.headers["Authorization"] = self.auth
        request.registry.settings = {"readonly": "true"}
        ping = heartbeat(self.storage)
        self.assertTrue(ping(request))

    def test_ping_returns_false_if_unavailable_in_readonly_mode(self):
        request = DummyRequest()
        request.headers["Authorization"] = self.auth
        request.registry.settings = {"readonly": "true"}
        ping = heartbeat(self.storage)
        with mock.patch.object(
            self.storage, "list_all", side_effect=exceptions.BackendError("Boom!")
        ):
            self.assertFalse(ping(request))

    def test_ping_logs_error_if_unavailable(self):
        request = DummyRequest()
        self.client_error_patcher.start()
        ping = heartbeat(self.storage)

        with mock.patch("kinto.core.storage.logger.exception") as exc_handler:
            self.assertFalse(ping(request))

        self.assertTrue(exc_handler.called)

    def test_ping_leaves_no_tombstone(self):
        request = DummyRequest()
        request.headers["Authorization"] = self.auth
        ping = heartbeat(self.storage)
        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.7):
            ping(request)
        with mock.patch("kinto.core.storage.random.SystemRandom.random", return_value=0.5):
            ping(request)
        objects = self.storage.list_all(
            parent_id="__heartbeat__", resource_name="__heartbeat__", include_deleted=True
        )
        self.assertEqual(len(objects), 0)

    def test_create_adds_the_object_id(self):
        obj = self.create_object()
        self.assertIsNotNone(obj["id"])

    def test_create_works_as_expected(self):
        stored = self.create_object()
        retrieved = self.storage.get(object_id=stored["id"], **self.storage_kw)
        self.assertEqual(retrieved, stored)

    def test_create_copies_the_object_before_modifying_it(self):
        self.create_object()
        self.assertEqual(self.obj.get("id"), None)

    def test_create_uses_the_resource_id_generator(self):
        obj = self.create_object(id_generator=lambda: OBJECT_ID)
        self.assertEqual(obj["id"], OBJECT_ID)

    def test_create_supports_unicode_for_parent_and_id(self):
        unicode_id = "Rémy"
        self.create_object(parent_id=unicode_id, resource_name=unicode_id)

    def test_create_does_not_overwrite_the_provided_id(self):
        obj = {**self.obj, self.id_field: OBJECT_ID}
        stored = self.create_object(obj=obj)
        self.assertEqual(stored[self.id_field], OBJECT_ID)

    def test_create_raise_unicity_error_if_provided_id_exists(self):
        obj = {**self.obj, self.id_field: OBJECT_ID}
        self.create_object(obj=obj)
        obj = {**self.obj, self.id_field: OBJECT_ID}
        self.assertRaises(exceptions.UnicityError, self.create_object, obj=obj)

    def test_create_does_generate_a_new_last_modified_field(self):
        obj = {**self.obj}
        self.assertNotIn(self.modified_field, obj)
        created = self.create_object(obj=obj)
        self.assertIn(self.modified_field, created)

    def test_get_raise_on_object_not_found(self):
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.get,
            object_id=OBJECT_ID,
            **self.storage_kw,
        )

    def test_update_creates_a_new_object_when_needed(self):
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.get,
            object_id=OBJECT_ID,
            **self.storage_kw,
        )
        obj = self.storage.update(object_id=OBJECT_ID, obj=self.obj, **self.storage_kw)
        retrieved = self.storage.get(object_id=OBJECT_ID, **self.storage_kw)
        self.assertEqual(retrieved, obj)

    def test_update_overwrites_object_id(self):
        stored = self.create_object()
        object_id = stored[self.id_field]
        self.obj[self.id_field] = "this-will-be-ignored"
        self.storage.update(object_id=object_id, obj=self.obj, **self.storage_kw)
        retrieved = self.storage.get(object_id=object_id, **self.storage_kw)
        self.assertEqual(retrieved[self.id_field], object_id)

    def test_update_generates_a_new_last_modified_field_if_not_present(self):
        stored = self.create_object()
        object_id = stored[self.id_field]
        self.assertNotIn(self.modified_field, self.obj)
        self.storage.update(object_id=object_id, obj=self.obj, **self.storage_kw)
        retrieved = self.storage.get(object_id=object_id, **self.storage_kw)
        self.assertIn(self.modified_field, retrieved)
        self.assertGreater(retrieved[self.modified_field], stored[self.modified_field])

    def test_delete_works_properly(self):
        stored = self.create_object()
        self.storage.delete(object_id=stored["id"], **self.storage_kw)
        self.assertRaises(  # Shouldn't exist.
            exceptions.ObjectNotFoundError,
            self.storage.get,
            object_id=stored["id"],
            **self.storage_kw,
        )

    def test_delete_works_even_on_second_time(self):
        # Create an object
        self.storage.create(resource_name="test", parent_id="1234", obj={"id": "demo"})
        # Delete the object
        self.storage.delete(
            resource_name="test", parent_id="1234", object_id="demo", with_deleted=True
        )
        # Update an object (it recreates it.)
        self.storage.update(
            resource_name="test", parent_id="1234", object_id="demo", obj={"id": "demo"}
        )
        # Delete the object without errors
        self.storage.delete(
            resource_name="test", parent_id="1234", object_id="demo", with_deleted=True
        )

    def test_delete_can_specify_the_last_modified(self):
        stored = self.create_object()
        last_modified = stored[self.modified_field] + 10
        self.storage.delete(object_id=stored["id"], last_modified=last_modified, **self.storage_kw)

        objects = self.storage.list_all(include_deleted=True, **self.storage_kw)
        self.assertEqual(objects[0][self.modified_field], last_modified)

    def test_delete_raise_when_unknown(self):
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.delete,
            object_id=OBJECT_ID,
            **self.storage_kw,
        )

    def test_list_all_handles_parent_id_pattern_matching(self):
        self.create_object(parent_id="abc", resource_name="c")
        obj = self.create_object(parent_id="abc", resource_name="c")
        self.storage.delete(object_id=obj["id"], parent_id="abc", resource_name="c")
        self.create_object(parent_id="efg", resource_name="c")

        objects = self.storage.list_all(parent_id="ab*", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 2)
        total_objects = self.storage.count_all(parent_id="ab*", resource_name="c")
        self.assertEqual(total_objects, 1)

    def test_list_all_does_proper_parent_id_pattern_matching(self):
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="xabcx", resource_name="c")
        self.create_object(parent_id="efg", resource_name="c")

        objects = self.storage.list_all(parent_id="ab*", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 1)
        total_objects = self.storage.count_all(parent_id="ab*", resource_name="c")
        self.assertEqual(len(objects), total_objects)

    def test_list_all_parent_id_handles_collisions(self):
        abc1 = self.create_object(
            parent_id="abc1", resource_name="c", obj={"id": "abc", "secret_data": "abc1"}
        )
        abc2 = self.create_object(
            parent_id="abc2", resource_name="c", obj={"id": "abc", "secret_data": "abc2"}
        )
        objects = self.storage.list_all(parent_id="ab*", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 2)
        total_objects = self.storage.count_all(parent_id="ab*", resource_name="c")
        self.assertEqual(len(objects), total_objects)
        objects.sort(key=lambda obj: obj["secret_data"])
        self.assertEqual(objects[0], abc1)
        self.assertEqual(objects[1], abc2)

    def test_return_all_values(self):
        for x in range(10):
            obj = dict(self.obj)
            obj["number"] = x
            self.create_object(obj)

        objects = self.storage.list_all(**self.storage_kw)
        self.assertEqual(len(objects), 10)
        total_objects = self.storage.count_all(**self.storage_kw)
        self.assertEqual(len(objects), total_objects)

    def test_list_all_handle_limit(self):
        for x in range(10):
            obj = dict(self.obj)
            obj["number"] = x
            self.create_object(obj)

        objects = self.storage.list_all(include_deleted=True, limit=2, **self.storage_kw)
        self.assertEqual(len(objects), 2)

    def test_list_all_handle_sorting_on_id(self):
        for x in range(3):
            self.create_object()
        sorting = [Sort("id", 1)]
        objects = self.storage.list_all(sorting=sorting, **self.storage_kw)
        self.assertTrue(objects[0]["id"] < objects[-1]["id"])

    def test_list_all_handle_sorting_on_subobject(self):
        for x in range(10):
            obj = dict(**self.obj)
            obj["person"] = dict(age=x)
            self.create_object(obj)
        sorting = [Sort("person.age", 1)]
        objects = self.storage.list_all(sorting=sorting, **self.storage_kw)
        self.assertLess(objects[0]["person"]["age"], objects[-1]["person"]["age"])

    def test_list_all_sorting_is_consistent_with_filtering(self):
        self.create_object({"flavor": "strawberry"})
        self.create_object({"flavor": "blueberry", "author": None})
        self.create_object({"flavor": "raspberry", "author": 1})
        self.create_object({"flavor": "orange", "author": True})
        self.create_object({"flavor": "watermelon", "author": "Ethan"})
        sorting = [Sort("author", 1)]
        objects = self.storage.list_all(sorting=sorting, **self.storage_kw)
        # Some interesting values to compare against
        values = ["A", "Z", "", 0, 4, MISSING]

        for value in values:
            # Together, these filters should provide the entire list
            filter_less = Filter("author", value, utils.COMPARISON.LT)
            filter_min = Filter("author", value, utils.COMPARISON.MIN)
            smaller_objects = self.storage.list_all(
                filters=[filter_less], sorting=sorting, **self.storage_kw
            )
            greater_objects = self.storage.list_all(
                filters=[filter_min], sorting=sorting, **self.storage_kw
            )
            other_objects = smaller_objects + greater_objects
            self.assertEqual(
                objects,
                other_objects,
                "Filtering is not consistent with sorting when filtering "
                "using value {}: {} (LT) + {} (MIN) != {}".format(
                    value, smaller_objects, greater_objects, objects
                ),
            )

        # Same test but with MAX and GT
        for value in values:
            # Together, these filters should provide the entire list
            filter_less = Filter("author", value, utils.COMPARISON.MAX)
            filter_min = Filter("author", value, utils.COMPARISON.GT)
            smaller_objects = self.storage.list_all(
                filters=[filter_less], sorting=sorting, **self.storage_kw
            )
            greater_objects = self.storage.list_all(
                filters=[filter_min], sorting=sorting, **self.storage_kw
            )
            other_objects = smaller_objects + greater_objects
            self.assertEqual(
                objects,
                other_objects,
                "Filtering is not consistent with sorting when filtering "
                "using value {}: {} (MAX) + {} (GT) != {}".format(
                    value, smaller_objects, greater_objects, objects
                ),
            )

    def test_list_all_can_filter_with_list_of_values(self):
        for code in ["a", "b", "c"]:
            self.create_object({"code": code})
        filters = [Filter("code", ["a", "b"], utils.COMPARISON.IN)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

    def test_list_all_can_filter_on_array_that_contains_values(self):
        self.create_object({"colors": ["red", "green", "blue"]})
        self.create_object({"colors": ["gray", "blue"]})
        self.create_object({"colors": ["red", "gray", "blue"]})
        self.create_object({"colors": ["purple", "green", "blue"]})

        filters = [Filter("colors", ["red"], utils.COMPARISON.CONTAINS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

        filters = [Filter("colors", ["red", "gray"], utils.COMPARISON.CONTAINS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_on_field_that_do_not_contains_an_array_with_contains_any(self):
        self.create_object({"colors": ["red", "green", "blue"]})
        self.create_object({"colors": {"html": "#00FF00"}})

        filters = [Filter("colors", ["red"], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

        filters = [Filter("colors", [{"html": "#00FF00"}], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)

    def test_list_all_can_filter_on_array_that_contains_any_value(self):
        self.create_object({"colors": ["red", "green", "blue"]})
        self.create_object({"colors": ["gray", "blue"]})
        self.create_object({"colors": ["red", "gray", "blue"]})
        self.create_object({"colors": ["purple", "green", "blue"]})

        filters = [Filter("colors", ["red"], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

        filters = [Filter("colors", ["red", "gray"], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 3)

    def test_list_all_can_filter_on_array_that_contains_numeric_values(self):
        self.create_object({"fib": [1, 2, 3]})
        self.create_object({"fib": [2, 3, 5]})
        self.create_object({"fib": [3, 5, 8]})
        self.create_object({"fib": [5, 8, 13]})

        filters = [Filter("fib", [2], utils.COMPARISON.CONTAINS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

        filters = [Filter("fib", [2, 3], utils.COMPARISON.CONTAINS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

    def test_list_all_can_filter_on_array_that_contains_any_numeric_value(self):
        self.create_object({"fib": [1, 2, 3]})
        self.create_object({"fib": [2, 3, 5]})
        self.create_object({"fib": [3, 5, 8]})
        self.create_object({"fib": [5, 8, 13]})

        filters = [Filter("fib", [2], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

        filters = [Filter("fib", [2, 3], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 3)

    def test_list_all_can_filter_on_array_with_contains_and_missing_field(self):
        self.create_object({"code": "black"})
        self.create_object({"fib": [2, 3, 5]})
        self.create_object({"fib": [3, 5, 8]})
        self.create_object({"fib": [5, 8, 13]})

        filters = [Filter("fib", [2], utils.COMPARISON.CONTAINS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_on_array_with_contains_any_and_missing_field(self):
        self.create_object({"code": "black"})
        self.create_object({"fib": [2, 3, 5]})
        self.create_object({"fib": [3, 5, 8]})
        self.create_object({"fib": [5, 8, 13]})

        filters = [Filter("fib", [2], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_on_array_with_contains_and_unsupported_type(self):
        self.create_object({"code": "black"})
        self.create_object({"fib": [2, 3, 5]})
        self.create_object({"fib": [3, 5, 8]})
        self.create_object({"fib": [5, 8, 13]})

        filters = [Filter("fib", [{"demo": "foobar"}], utils.COMPARISON.CONTAINS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)

    def test_list_all_can_filter_on_array_with_contains_any_and_unsupported_type(self):
        self.create_object({"code": "black"})
        self.create_object({"fib": [2, 3, 5]})
        self.create_object({"fib": [3, 5, 8]})
        self.create_object({"fib": [5, 8, 13]})

        filters = [Filter("fib", [{"demo": "foobar"}], utils.COMPARISON.CONTAINS_ANY)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)

    def test_list_all_can_filter_with_numeric_values(self):
        self.create_object({"missing": "code"})
        for code in [1, 10, 6, 46]:
            self.create_object({"code": code})

        sorting = [Sort("code", 1)]
        filters = [Filter("code", 10, utils.COMPARISON.MAX)]
        objects = self.storage.list_all(sorting=sorting, filters=filters, **self.storage_kw)
        self.assertEqual(objects[0]["code"], 1)
        self.assertEqual(objects[1]["code"], 6)
        self.assertEqual(objects[2]["code"], 10)
        self.assertEqual(len(objects), 3)

        filters = [Filter("code", 10, utils.COMPARISON.LT)]
        objects = self.storage.list_all(sorting=sorting, filters=filters, **self.storage_kw)
        self.assertEqual(objects[0]["code"], 1)
        self.assertEqual(objects[1]["code"], 6)
        self.assertEqual(len(objects), 2)

    def test_list_all_can_filter_with_numeric_id(self):
        for code in [0, 42]:
            self.create_object({"id": str(code)})

        filters = [Filter("id", 0, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

        filters = [Filter("id", 42, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_with_numeric_strings(self):
        for code in ["0566199093", "0781566199"]:
            self.create_object({"phone": code})
        filters = [Filter("phone", "0566199093", utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_with_empty_numeric_strings(self):
        for code in ["0566199093", "0781566199"]:
            self.create_object({"phone": code})
        filters = [Filter("phone", "", utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)

    def test_list_all_can_filter_with_float_values(self):
        for code in [10, 11.5, 8.5, 6, 7.5]:
            self.create_object({"note": code})
        filters = [Filter("note", 9.5, utils.COMPARISON.LT)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 3)

    def test_list_all_can_filter_with_strings(self):
        for code in ["Rémy", "Alexis", "Marie"]:
            self.create_object({"name": code})
        sorting = [Sort("name", 1)]
        filters = [Filter("name", "Mathieu", utils.COMPARISON.LT)]
        objects = self.storage.list_all(sorting=sorting, filters=filters, **self.storage_kw)
        self.assertEqual(objects[0]["name"], "Alexis")
        self.assertEqual(objects[1]["name"], "Marie")
        self.assertEqual(len(objects), 2)

    def test_list_all_can_filter_minimum_value_with_strings(self):
        for v in ["49.0", "6.0", "53.0b4"]:
            self.create_object({"product": {"version": v}})
        sorting = [Sort("product.version", 1)]
        filters = [Filter("product.version", "50.0", utils.COMPARISON.MIN)]
        objects = self.storage.list_all(sorting=sorting, filters=filters, **self.storage_kw)
        self.assertEqual(objects[0]["product"]["version"], "53.0b4")
        self.assertEqual(objects[1]["product"]["version"], "6.0")
        self.assertEqual(len(objects), 2)

    def test_list_all_does_not_implicitly_cast(self):
        for v in ["49.0", "6.0", "53.0b4"]:
            self.create_object({"product": {"version": v}})
        sorting = [Sort("product.version", 1)]
        filters = [Filter("product.version", 50.0, utils.COMPARISON.MIN)]
        objects = self.storage.list_all(sorting=sorting, filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)  # 50 (number) > strings

    def test_list_all_can_deal_with_none_values(self):
        self.create_object({"name": "Alexis"})
        self.create_object({"title": "haha"})
        self.create_object({"name": "Mathieu"})
        filters = [Filter("name", "Fanny", utils.COMPARISON.GT)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        # NULLs compare as greater than everything
        self.assertEqual(len(objects), 2)
        # But we aren't clear on what the order will be
        mathieu_object = objects[0] if "name" in objects[0] else objects[1]
        haha_object = objects[1] if "name" in objects[0] else objects[0]
        self.assertEqual(mathieu_object["name"], "Mathieu")
        self.assertEqual(haha_object["title"], "haha")

        filters = [Filter("name", "Fanny", utils.COMPARISON.LT)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["name"], "Alexis")

    def test_list_all_can_filter_with_none_values(self):
        self.create_object({"name": "Alexis", "salary": None})
        self.create_object({"name": "Mathieu", "salary": "null"})
        self.create_object({"name": "Niko", "salary": ""})
        self.create_object({"name": "Ethan"})  # missing salary
        filters = [Filter("salary", None, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["name"], "Alexis")

    def test_filter_none_values_can_be_combined(self):
        self.create_object({"name": "Alexis", "salary": None})
        self.create_object({"name": "Mathieu", "salary": "null"})
        self.create_object({"name": "Niko", "salary": ""})
        self.create_object({"name": "Ethan"})  # missing salary
        filters = [
            Filter("salary", 0, utils.COMPARISON.GT),
            Filter("salary", True, utils.COMPARISON.HAS),
        ]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len([r for r in objects if "salary" not in r]), 0)

    def test_list_all_can_filter_with_list_of_values_on_id(self):
        object1 = self.create_object({"code": "a"})
        object2 = self.create_object({"code": "b"})
        filters = [Filter("id", [object1["id"], object2["id"]], utils.COMPARISON.IN)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

    def test_list_all_returns_empty_when_including_list_of_empty_values(self):
        self.create_object({"code": "a"})
        self.create_object({"code": "b"})
        filters = [Filter("id", [], utils.COMPARISON.IN)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)

    def test_list_all_can_filter_with_list_of_excluded_values(self):
        for code in ["a", "b", "c"]:
            self.create_object({"code": code})
        filters = [Filter("code", ("a", "b"), utils.COMPARISON.EXCLUDE)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_a_list_of_integer_values(self):
        for code in [1, 2, 3]:
            self.create_object({"code": code})
        filters = [Filter("code", (1, 2), utils.COMPARISON.EXCLUDE)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_a_list_of_mixed_typed_values(self):
        for code in [1, 2, 3]:
            self.create_object({"code": code})
        filters = [Filter("code", (1, "b"), utils.COMPARISON.EXCLUDE)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

    def test_list_all_can_filter_a_list_of_integer_values_on_subobjects(self):
        for code in [1, 2, 3]:
            self.create_object({"code": {"city": code}})
        filters = [Filter("code.city", (1, 2), utils.COMPARISON.EXCLUDE)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_matching_a_list(self):
        self.create_object({"flavor": "strawberry", "orders": []})
        self.create_object({"flavor": "blueberry", "orders": [1]})
        self.create_object({"flavor": "pineapple", "orders": [1, 2]})
        self.create_object({"flavor": "watermelon", "orders": ""})
        self.create_object({"flavor": "raspberry", "orders": {}})
        filters = [Filter("orders", [], utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["flavor"], "strawberry")

        filters = [Filter("orders", [1], utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["flavor"], "blueberry")

    def test_list_all_can_filter_matching_an_object(self):
        self.create_object({"flavor": "strawberry", "attributes": {}})
        self.create_object(
            {"flavor": "blueberry", "attributes": {"ibu": 25, "seen_on": "2017-06-01"}}
        )
        self.create_object(
            {
                "flavor": "watermelon",
                "attributes": {"ibu": 25, "seen_on": "2017-06-01", "price": 9.99},
            }
        )
        self.create_object({"flavor": "raspberry", "attributes": []})
        filters = [Filter("attributes", {}, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["flavor"], "strawberry")

        filters = [Filter("attributes", {"ibu": 25, "seen_on": "2017-06-01"}, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["flavor"], "blueberry")

    def test_list_all_supports_has(self):
        self.create_object({"flavor": "strawberry"})
        self.create_object({"flavor": "blueberry", "author": None})
        self.create_object({"flavor": "raspberry", "author": ""})
        self.create_object({"flavor": "watermelon", "author": "hello"})
        self.create_object({"flavor": "pineapple", "author": "null"})
        filters = [Filter("author", True, utils.COMPARISON.HAS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 4)
        self.assertEqual(
            sorted([r["flavor"] for r in objects]),
            ["blueberry", "pineapple", "raspberry", "watermelon"],
        )

        filters = [Filter("author", False, utils.COMPARISON.HAS)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["flavor"], "strawberry")

    def test_list_all_can_filter_by_subobjects_values(self):
        for code in ["a", "b", "c"]:
            self.create_object({"code": {"sub": code}})
        filters = [Filter("code.sub", "a", utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)

    def test_list_all_can_filter_with_like_and_implicit_wildchars(self):
        self.create_object({"name": "foo"})
        self.create_object({"name": "aafooll"})
        self.create_object({"name": "bar"})
        self.create_object({"name": "FOOBAR"})

        filters = [Filter("name", "FoO", utils.COMPARISON.LIKE)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 3)

    def test_list_all_can_filter_with_wildchars(self):
        self.create_object({"name": "eabcg"})
        self.create_object({"name": "aabcc"})
        self.create_object({"name": "abc"})
        self.create_object({"name": "aec"})
        self.create_object({"name": "efg"})

        filters = [Filter("name", "a*b*c", utils.COMPARISON.LIKE)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 2)

    def test_objects_filtered_when_searched_by_string_field(self):
        self.create_object({"name": "foo"})
        self.create_object({"name": "bar"})
        self.create_object({"name": "FOOBAR"})

        filters = [Filter("name", "FoO", utils.COMPARISON.LIKE)]
        results = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(results), 2)


class TimestampsTest:
    def test_timestamp_are_incremented_on_create(self):
        self.create_object()  # init
        before = self.storage.resource_timestamp(**self.storage_kw)
        self.create_object()
        after = self.storage.resource_timestamp(**self.storage_kw)
        self.assertTrue(before < after)

    def test_timestamp_are_incremented_on_update(self):
        stored = self.create_object()
        _id = stored["id"]
        before = self.storage.resource_timestamp(**self.storage_kw)
        self.storage.update(object_id=_id, obj={"bar": "foo"}, **self.storage_kw)
        after = self.storage.resource_timestamp(**self.storage_kw)
        self.assertTrue(before < after)

    def test_timestamp_are_incremented_on_delete(self):
        stored = self.create_object()
        _id = stored["id"]
        before = self.storage.resource_timestamp(**self.storage_kw)
        self.storage.delete(object_id=_id, **self.storage_kw)
        after = self.storage.resource_timestamp(**self.storage_kw)
        self.assertTrue(before < after)

    @skip_if_ci
    def test_timestamps_are_unique(self):  # pragma: no cover
        obtained = []

        def create_item():
            for i in range(100):
                obj = self.create_object()
                obtained.append((obj["last_modified"], obj["id"]))

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

    def test_the_timestamp_is_not_updated_when_resource_remains_empty(self):
        # Get timestamp once.
        first = self.storage.resource_timestamp(**self.storage_kw)

        time.sleep(0.002)  # wait some time.

        # Check that second time returns the same value.
        second = self.storage.resource_timestamp(**self.storage_kw)
        self.assertEqual(first, second)

    def test_the_timestamp_are_based_on_real_time_milliseconds(self):
        before = utils.msec_time()
        time.sleep(0.002)  # 2 msec
        obj = self.create_object()
        now = obj["last_modified"]
        time.sleep(0.002)  # 2 msec
        after = utils.msec_time()
        self.assertTrue(before < now < after, f"{before} < {now} < {after}")

    def test_timestamp_are_always_incremented_above_existing_value(self):
        # Create an object with normal clock
        obj = self.create_object()
        current = obj["last_modified"]

        # Patch the clock to return a time in the past, before the big bang
        with mock.patch("kinto.core.utils.msec_time") as time_mocked:
            time_mocked.return_value = -1

            obj = self.create_object()
            after = obj["last_modified"]

        # Expect the last one to be based on the highest value
        self.assertTrue(0 < current < after, f"0 < {current} < {after}")

    def test_resource_timestamp_raises_error_when_empty_and_readonly(self):
        kw = {**self.storage_kw, "resource_name": "will-be-empty"}
        self.storage.readonly = True
        with self.assertRaises(exceptions.BackendError):
            self.storage.resource_timestamp(**kw)
        self.storage.readonly = False

    def test_resource_timestamp_returns_current_while_readonly(self):
        kw = {**self.storage_kw, "resource_name": "will-be-empty"}
        ts1 = self.storage.resource_timestamp(**kw)
        self.storage.readonly = True
        ts2 = self.storage.resource_timestamp(**kw)
        self.assertEqual(ts1, ts2)
        self.storage.readonly = False

    def test_create_uses_specified_last_modified_if_resource_empty(self):
        # Resource is empty, create a new object that contains a timestamp.
        last_modified = 1_448_881_675_541
        obj = {**self.obj, self.id_field: OBJECT_ID, self.modified_field: last_modified}
        self.create_object(obj=obj)

        # Check that the object was assigned the specified timestamp.
        retrieved = self.storage.get(object_id=OBJECT_ID, **self.storage_kw)
        self.assertEqual(retrieved[self.modified_field], last_modified)

        # Resource timestamp is now the same as its only object.
        resource_ts = self.storage.resource_timestamp(**self.storage_kw)
        self.assertEqual(resource_ts, last_modified)

    def test_create_ignores_specified_last_modified_if_in_the_past(self):
        # Create a first object, and get the timestamp.
        first_object = self.create_object()
        timestamp_before = first_object[self.modified_field]

        # Create a new object with its timestamp in the past.
        obj = {**self.obj, self.id_field: OBJECT_ID, self.modified_field: timestamp_before - 10}
        self.create_object(obj=obj)

        # Check that object timestamp is the one specified.
        retrieved = self.storage.get(object_id=OBJECT_ID, **self.storage_kw)
        self.assertLess(retrieved[self.modified_field], timestamp_before)
        self.assertEqual(retrieved[self.modified_field], obj[self.modified_field])

        # Check that resource timestamp was not changed. Someone importing
        # objects in the past must assume the synchronization consequences.
        timestamp = self.storage.resource_timestamp(**self.storage_kw)
        self.assertEqual(timestamp, timestamp_before)

    def test_create_ignores_specified_last_modified_if_equal(self):
        # Create a first object, and get the timestamp.
        first_object = self.create_object()
        timestamp_before = first_object[self.modified_field]

        # Create a new object with its timestamp in the past.
        obj = {**self.obj, self.id_field: OBJECT_ID, self.modified_field: timestamp_before}
        self.create_object(obj=obj)

        # Check that object timestamp is the one specified.
        retrieved = self.storage.get(object_id=OBJECT_ID, **self.storage_kw)
        self.assertGreater(retrieved[self.modified_field], timestamp_before)
        self.assertGreater(retrieved[self.modified_field], obj[self.modified_field])

        # Check that resource timestamp was bumped (change happened).
        timestamp = self.storage.resource_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)

    def test_update_uses_specified_last_modified_if_in_future(self):
        stored = self.create_object()
        object_id = stored[self.id_field]
        timestamp_before = stored[self.modified_field]

        # Set timestamp manually in the future.
        stored[self.modified_field] = timestamp_before + 10
        self.storage.update(object_id=object_id, obj=stored, **self.storage_kw)

        # Check that object timestamp is the one specified.
        retrieved = self.storage.get(object_id=object_id, **self.storage_kw)
        self.assertGreater(retrieved[self.modified_field], timestamp_before)
        self.assertGreaterEqual(retrieved[self.modified_field], stored[self.modified_field])

        # Check that resource timestamp took the one specified (in future).
        timestamp = self.storage.resource_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)
        self.assertEqual(timestamp, retrieved[self.modified_field])

    def test_update_ignores_specified_last_modified_if_in_the_past(self):
        stored = self.create_object()
        object_id = stored[self.id_field]
        timestamp_before = self.storage.resource_timestamp(**self.storage_kw)

        # Set timestamp manually in the past.
        stored[self.modified_field] = timestamp_before - 10
        self.storage.update(object_id=object_id, obj=stored, **self.storage_kw)

        # Check that object timestamp is the one specified.
        retrieved = self.storage.get(object_id=object_id, **self.storage_kw)
        self.assertLess(retrieved[self.modified_field], timestamp_before)
        self.assertEqual(retrieved[self.modified_field], stored[self.modified_field])

        # Check that resource timestamp was not changed. Someone importing
        # objects in the past must assume the synchronization consequences.
        timestamp = self.storage.resource_timestamp(**self.storage_kw)
        self.assertEqual(timestamp, timestamp_before)

    def test_update_ignores_specified_last_modified_if_equal(self):
        stored = self.create_object()
        object_id = stored[self.id_field]
        timestamp_before = stored[self.modified_field]

        # Do not change the timestamp.
        self.storage.update(object_id=object_id, obj=stored, **self.storage_kw)

        # Check that object timestamp was bumped.
        retrieved = self.storage.get(object_id=object_id, **self.storage_kw)
        self.assertGreater(retrieved[self.modified_field], timestamp_before)
        self.assertGreater(retrieved[self.modified_field], stored[self.modified_field])

        # Check that resource timestamp was bumped (change happened).
        timestamp = self.storage.resource_timestamp(**self.storage_kw)
        self.assertGreater(timestamp, timestamp_before)

    def test_legacy_get_all_works_with_deprecation_warning(self):
        self.create_object(parent_id="abc", resource_name="c")
        obj = self.create_object(parent_id="abc", resource_name="c")
        self.storage.delete(object_id=obj["id"], parent_id="abc", resource_name="c")
        self.create_object(parent_id="abe", resource_name="c")

        pagination = [[Filter("last_modified", 314, utils.COMPARISON.GT)]]
        sorting = [Sort("last_modified", 1)]
        objects, count = self.storage.get_all(
            parent_id="ab*",
            resource_name="c",
            include_deleted=True,
            # sorting, limits, and pagination doesn't make sense for counting but it should
            # not complain when you use the legacy get_all.
            sorting=sorting,
            pagination_rules=pagination,
            limit=99,
        )
        self.assertEqual(len(objects), 3)
        self.assertEqual(count, 2)
        print(self.mocked_warnings.mock_calls)
        message = "Use either self.list_all() or self.count_all()"
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)


class DeletedObjectsTest:
    def _get_last_modified_filters(self):
        start = self.storage.resource_timestamp(**self.storage_kw)
        time.sleep(0.1)
        return [Filter(self.modified_field, start, utils.COMPARISON.GT)]

    def create_and_delete_object(self, obj=None):
        """Helper to create and delete an object."""
        obj = obj or {"challenge": "accepted"}
        obj = self.create_object(obj)
        time.sleep(0.001)  # 1 msec
        deleted = self.storage.delete(object_id=obj["id"], **self.storage_kw)
        time.sleep(0.001)  # 1 msec
        return deleted

    def test_get_should_not_return_deleted_items(self):
        obj = self.create_and_delete_object()
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.get,
            object_id=obj["id"],
            **self.storage_kw,
        )

    def test_deleting_a_deleted_item_should_raise_not_found(self):
        obj = self.create_and_delete_object()
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.delete,
            object_id=obj["id"],
            **self.storage_kw,
        )

    def test_recreating_a_deleted_object_should_delete_its_tombstone(self):
        obj = {"id": "jesus", "rebirth": True}
        self.create_and_delete_object(obj)
        self.create_object(obj)
        objects = self.storage.list_all(include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 1)  # No tombstone.
        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 1)  # One existing.

    def test_deleting_a_object_twice_should_update_its_tombstone(self):
        obj = {"id": "jesus", "rebirth": True}
        deleted = self.create_and_delete_object(obj)
        before = deleted["last_modified"]
        deleted = self.create_and_delete_object(obj)
        after = deleted["last_modified"]
        self.assertNotEqual(before, after)

    def test_deleted_items_have_deleted_set_to_true(self):
        obj = self.create_and_delete_object()
        self.assertTrue(obj["deleted"])

    def test_deleted_items_have_only_basic_fields(self):
        obj = self.create_and_delete_object()
        self.assertIn("id", obj)
        self.assertIn("last_modified", obj)
        self.assertNotIn("challenge", obj)

    def test_last_modified_of_a_deleted_item_is_deletion_time(self):
        before = self.storage.resource_timestamp(**self.storage_kw)
        obj = self.create_and_delete_object()
        now = self.storage.resource_timestamp(**self.storage_kw)
        self.assertEqual(now, obj["last_modified"])
        self.assertTrue(before < obj["last_modified"])

    def test_list_all_does_not_include_deleted_items_by_default(self):
        self.create_and_delete_object()
        objects = self.storage.list_all(**self.storage_kw)
        self.assertEqual(len(objects), 0)

    def test_list_all_count_does_not_include_deleted_items(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_object()
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    def test_list_all_can_return_deleted_items(self):
        filters = self._get_last_modified_filters()
        obj = self.create_and_delete_object()
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        deleted = objects[0]
        self.assertEqual(deleted["id"], obj["id"])
        self.assertEqual(deleted["last_modified"], obj["last_modified"])
        self.assertEqual(deleted["deleted"], True)
        self.assertNotIn("challenge", deleted)

    def test_delete_all_keeps_track_of_deleted_objects(self):
        filters = self._get_last_modified_filters()
        obj = {"challenge": "accepted"}
        obj = self.create_object(obj)
        self.storage.delete_all(**self.storage_kw)
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    def test_delete_all_can_delete_without_tombstones(self):
        # Create 2 objects, one becomes tombstone.
        filters = self._get_last_modified_filters()
        r = self.create_and_delete_object()
        self.create_object({"challenge": "accepted"})

        # Delete objects, without creating new tombstones.
        old = self.storage.delete_all(filters=filters, with_deleted=False, **self.storage_kw)
        self.assertEqual(len(old), 1)  # Not 2, because one is tombstone.

        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        self.assertTrue(objects[0]["deleted"])
        self.assertTrue(objects[0]["id"], r["id"])
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    def test_delete_can_delete_without_tombstones(self):
        filters = self._get_last_modified_filters()
        obj = {"challenge": "accepted"}
        obj = self.create_object(obj)
        self.storage.delete(object_id=obj["id"], with_deleted=False, **self.storage_kw)
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 0)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    def test_deleting_without_tombstone_should_raise_not_found(self):
        obj = self.create_and_delete_object()
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.delete,
            object_id=obj["id"],
            with_deleted=False,
            **self.storage_kw,
        )

    def test_delete_all_deletes_objects(self):
        self.create_object()
        self.create_object()

        self.storage.delete_all(**self.storage_kw)

        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 0)

    def test_delete_all_bumps_collection_timestamp(self):
        self.create_object()
        self.create_object()
        timestamp_before = self.storage.resource_timestamp(**self.storage_kw)

        self.storage.delete_all(**self.storage_kw)

        timestamp_after = self.storage.resource_timestamp(**self.storage_kw)
        self.assertNotEqual(timestamp_after, timestamp_before)

    def test_delete_all_keeps_tombstones(self):
        self.create_object()
        self.create_object()

        self.storage.delete_all(**self.storage_kw)

        self.assertEqual(len(self.storage.list_all(include_deleted=True, **self.storage_kw)), 2)

    def test_delete_all_bumps_tombstones_timestamps(self):
        self.create_object()
        self.create_object()
        timestamps_before = {r["last_modified"] for r in self.storage.list_all(**self.storage_kw)}

        self.storage.delete_all(**self.storage_kw)

        timestamps_after = {
            r["last_modified"]
            for r in self.storage.list_all(include_deleted=True, **self.storage_kw)
        }
        self.assertTrue(timestamps_after.isdisjoint(timestamps_before))

    def test_delete_all_can_delete_by_parent_id(self):
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="efg", resource_name="c")
        self.storage.delete_all(parent_id="ab*", resource_name=None, with_deleted=False)
        objects = self.storage.list_all(parent_id="abc", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 0)
        count = self.storage.count_all(parent_id="abc", resource_name="c")
        self.assertEqual(count, 0)
        objects = self.storage.list_all(parent_id="efg", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(parent_id="efg", resource_name="c")
        self.assertEqual(count, 1)

    def test_delete_all_does_proper_parent_id_matching(self):
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="xabcx", resource_name="c")
        self.create_object(parent_id="efg", resource_name="c")
        self.storage.delete_all(parent_id="ab*", resource_name=None, with_deleted=False)
        objects = self.storage.list_all(parent_id="xabcx", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(parent_id="xabcx", resource_name="c")
        self.assertEqual(count, 1)
        objects = self.storage.list_all(parent_id="efg", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(parent_id="efg", resource_name="c")
        self.assertEqual(count, 1)

    def test_delete_all_does_proper_matching(self):
        self.create_object(parent_id="abc", resource_name="c", obj={"id": "id1"})
        self.create_object(parent_id="def", resource_name="g", obj={"id": "id1"})
        self.storage.delete_all(parent_id="ab*", resource_name=None, with_deleted=False)
        objects = self.storage.list_all(parent_id="def", resource_name="g", include_deleted=True)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(parent_id="def", resource_name="g")
        self.assertEqual(count, 1)

    def test_delete_all_can_delete_by_parent_id_with_tombstones(self):
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="efg", resource_name="c")
        self.storage.delete_all(parent_id="ab*", resource_name=None, with_deleted=True)
        objects = self.storage.list_all(parent_id="efg", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(parent_id="efg", resource_name="c")
        self.assertEqual(count, 1)

        objects = self.storage.list_all(parent_id="abc", resource_name="c", include_deleted=True)
        self.assertEqual(len(objects), 2)
        self.assertTrue(objects[0]["deleted"])
        self.assertTrue(objects[1]["deleted"])
        count = self.storage.count_all(parent_id="abc", resource_name="c")
        self.assertEqual(count, 0)

    def test_delete_all_can_delete_partially(self):
        self.create_object({"foo": "po"})
        self.create_object()
        filters = [Filter("foo", "bar", utils.COMPARISON.EQ)]
        self.storage.delete_all(filters=filters, **self.storage_kw)
        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 1)

    def test_delete_all_supports_limit(self):
        self.create_object()
        self.create_object()
        self.storage.delete_all(limit=1, **self.storage_kw)
        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 1)

    def test_delete_all_supports_sorting(self):
        for i in range(5):
            self.create_object({"foo": i})
        sorting = [Sort("foo", -1)]
        self.storage.delete_all(limit=2, sorting=sorting, **self.storage_kw)
        objects = self.storage.list_all(sorting=sorting, **self.storage_kw)
        self.assertEqual(objects[0]["foo"], 2)

    def test_purge_deleted_remove_all_tombstones(self):
        self.create_object()
        self.create_object()
        self.storage.delete_all(**self.storage_kw)
        num_removed = self.storage.purge_deleted(**self.storage_kw)
        self.assertEqual(num_removed, 2)
        objects = self.storage.list_all(include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 0)
        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 0)

    def test_purge_deleted_remove_all_tombstones_by_parent_id(self):
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="abc", resource_name="c")
        self.create_object(parent_id="efg", resource_name="c")
        self.storage.delete_all(parent_id="abc", resource_name="c")
        self.storage.delete_all(parent_id="efg", resource_name="c")
        num_removed = self.storage.purge_deleted(parent_id="ab*", resource_name=None)
        self.assertEqual(num_removed, 2)

    def test_purge_deleted_removes_timestamps_by_parent_id(self):
        self.create_object(parent_id="/abc/a", resource_name="c")
        self.create_object(parent_id="/abc/a", resource_name="c")
        self.create_object(parent_id="/efg", resource_name="c")

        before1 = self.storage.resource_timestamp(parent_id="/abc/a", resource_name="c")
        # Different parent_id with object.
        before2 = self.storage.resource_timestamp(parent_id="/efg", resource_name="c")
        # Different parent_id without object.
        before3 = self.storage.resource_timestamp(parent_id="/ijk", resource_name="c")

        self.storage.delete_all(parent_id="/abc/*", resource_name=None, with_deleted=False)
        self.storage.purge_deleted(parent_id="/abc/*", resource_name=None)

        after1 = self.storage.resource_timestamp(parent_id="/abc/a", resource_name="c")
        after2 = self.storage.resource_timestamp(parent_id="/efg", resource_name="c")
        after3 = self.storage.resource_timestamp(parent_id="/ijk", resource_name="c")

        self.assertNotEqual(before1, after1)
        self.assertEqual(before2, after2)
        self.assertEqual(before3, after3)

    def test_purge_deleted_works_when_no_tombstones(self):
        num_removed = self.storage.purge_deleted(**self.storage_kw)
        self.assertEqual(num_removed, 0)

    def test_purge_deleted_remove_with_before_remove_olders_exclusive(self):
        older = self.create_object()
        newer = self.create_object()
        self.storage.delete(object_id=older["id"], **self.storage_kw)
        self.storage.delete(object_id=newer["id"], **self.storage_kw)
        objects = self.storage.list_all(include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 2)
        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 0)
        num_removed = self.storage.purge_deleted(
            before=max([r["last_modified"] for r in objects]), **self.storage_kw
        )
        self.assertEqual(num_removed, 1)
        objects = self.storage.list_all(include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(**self.storage_kw)
        self.assertEqual(count, 0)

    #
    # Sorting
    #

    def test_sorting_on_last_modified_applies_to_deleted_items(self):
        filters = self._get_last_modified_filters()
        first = last = None
        for i in range(20, 0, -1):
            obj = self.create_and_delete_object()
            first = obj if i == 1 else first
            last = obj if i == 20 else last

        sorting = [Sort("last_modified", -1)]
        objects = self.storage.list_all(
            sorting=sorting, filters=filters, include_deleted=True, **self.storage_kw
        )

        self.assertDictEqual(objects[0], first)
        self.assertDictEqual(objects[-1], last)

    def test_sorting_on_last_modified_mixes_deleted_objects(self):
        filters = self._get_last_modified_filters()
        self.create_and_delete_object()
        self.create_object()
        self.create_and_delete_object()

        sorting = [Sort("last_modified", 1)]
        objects = self.storage.list_all(
            sorting=sorting, filters=filters, include_deleted=True, **self.storage_kw
        )

        self.assertIn("deleted", objects[0])
        self.assertNotIn("deleted", objects[1])
        self.assertIn("deleted", objects[2])

    def test_sorting_on_arbitrary_field_groups_deleted_at_last(self):
        filters = self._get_last_modified_filters()
        self.create_object({"status": 0})
        self.create_and_delete_object({"status": 1})
        self.create_and_delete_object({"status": 2})

        sorting = [Sort("status", 1)]
        objects = self.storage.list_all(
            sorting=sorting, filters=filters, include_deleted=True, **self.storage_kw
        )
        self.assertNotIn("deleted", objects[0])
        self.assertIn("deleted", objects[1])
        self.assertIn("deleted", objects[2])

    def test_support_sorting_on_deleted_field_groups_deleted_at_first(self):
        filters = self._get_last_modified_filters()
        # Respect boolean sort order
        self.create_and_delete_object()
        self.create_object()
        self.create_and_delete_object()

        sorting = [Sort("deleted", 1)]
        objects = self.storage.list_all(
            sorting=sorting, filters=filters, include_deleted=True, **self.storage_kw
        )
        self.assertIn("deleted", objects[0])
        self.assertIn("deleted", objects[1])
        self.assertNotIn("deleted", objects[2])

    def test_sorting_on_numeric_arbitrary_field(self):
        filters = self._get_last_modified_filters()
        for code in [1, 10, 6, 46]:
            self.create_object({"status": code})

        sorting = [Sort("status", -1)]
        objects = self.storage.list_all(
            sorting=sorting, filters=filters, include_deleted=True, **self.storage_kw
        )
        self.assertEqual(objects[0]["status"], 46)
        self.assertEqual(objects[1]["status"], 10)
        self.assertEqual(objects[2]["status"], 6)
        self.assertEqual(objects[3]["status"], 1)

    #
    # Filtering
    #

    def test_filtering_on_last_modified_applies_to_deleted_items(self):
        self.create_and_delete_object()
        filters = self._get_last_modified_filters()
        self.create_object()
        self.create_and_delete_object()

        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 2)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 1)

    def test_filtering_on_arbitrary_field_excludes_deleted_objects(self):
        filters = self._get_last_modified_filters()
        self.create_object({"status": 0})
        self.create_and_delete_object({"status": 0})

        filters += [Filter("status", 0, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 1)

    def test_support_filtering_on_deleted_field(self):
        filters = self._get_last_modified_filters()
        self.create_object()
        self.create_and_delete_object()

        filters += [Filter("deleted", True, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertIn("deleted", objects[0])
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    def test_support_filtering_out_on_deleted_field(self):
        filters = self._get_last_modified_filters()
        self.create_object()
        self.create_and_delete_object()

        filters += [Filter("deleted", True, utils.COMPARISON.NOT)]
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertNotIn("deleted", objects[0])
        self.assertEqual(len(objects), 1)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 1)

    def test_return_empty_set_if_filtering_on_deleted_false(self):
        filters = self._get_last_modified_filters()
        self.create_object()
        self.create_and_delete_object()

        filters += [Filter("deleted", False, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, include_deleted=True, **self.storage_kw)
        self.assertEqual(len(objects), 0)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    def test_return_empty_set_if_filtering_on_deleted_without_include(self):
        self.create_object()
        self.create_and_delete_object()

        filters = [Filter("deleted", True, utils.COMPARISON.EQ)]
        objects = self.storage.list_all(filters=filters, **self.storage_kw)
        self.assertEqual(len(objects), 0)
        count = self.storage.count_all(filters=filters, **self.storage_kw)
        self.assertEqual(count, 0)

    #
    # Pagination
    #

    def test_pagination_rules_on_last_modified_apply_to_deleted_objects(self):
        filters = self._get_last_modified_filters()
        for i in range(15):
            if i % 2 == 0:
                self.create_and_delete_object()
            else:
                self.create_object()

        pagination = [[Filter("last_modified", 314, utils.COMPARISON.GT)]]
        sorting = [Sort("last_modified", 1)]
        objects = self.storage.list_all(
            sorting=sorting,
            pagination_rules=pagination,
            limit=5,
            filters=filters,
            include_deleted=True,
            **self.storage_kw,
        )
        self.assertEqual(len(objects), 5)
        self.assertIn("deleted", objects[0])
        self.assertNotIn("deleted", objects[1])

    def test_pagination_can_skip_everything(self):
        for i in range(5):
            self.create_object({"i": i})

        pagination = [[Filter("i", 7, utils.COMPARISON.GT)]]
        objects = self.storage.list_all(
            pagination_rules=pagination, limit=5, include_deleted=True, **self.storage_kw
        )
        self.assertEqual(len(objects), 0)

    def test_list_all_handle_a_pagination_rules(self):
        for x in range(10):
            obj = dict(self.obj)
            obj["number"] = x % 3
            self.create_object(obj)

        objects = self.storage.list_all(
            limit=5,
            pagination_rules=[[Filter("number", 1, utils.COMPARISON.GT)]],
            **self.storage_kw,
        )
        self.assertEqual(len(objects), 3)

    def test_list_all_handle_all_pagination_rules(self):
        for x in range(10):
            obj = dict(self.obj)
            obj["number"] = x % 3
            last_object = self.create_object(obj)

        objects = self.storage.list_all(
            limit=5,
            pagination_rules=[
                [Filter("number", 1, utils.COMPARISON.GT)],
                [Filter("id", last_object["id"], utils.COMPARISON.EQ)],
            ],
            **self.storage_kw,
        )
        self.assertEqual(len(objects), 4)

    def test_list_all_parent_id_paginates_correctly(self):
        """Verify that pagination doesn't squash or duplicate some objects"""

        # Create objects with different parent IDs, but the same
        # object ID.
        for parent in range(10):
            parent_id = f"abc{parent}"
            self.storage.create(
                parent_id=parent_id,
                resource_name="c",
                obj={"id": "some_id", "secret_data": parent_id},
            )

        real_objects = self.storage.list_all(parent_id="abc*", resource_name="c")
        self.assertEqual(len(real_objects), 10)

        def sort_by_secret_data(records):
            return sorted(records, key=lambda r: r["secret_data"])

        GT = utils.COMPARISON.GT
        LT = utils.COMPARISON.LT
        for order in [("secret_data", 1), ("secret_data", -1)]:
            sort = [Sort(*order), Sort("last_modified", -1)]
            for limit in range(1, 10):
                with self.subTest(order=order, limit=limit):
                    objects = []
                    pagination = None
                    while True:
                        page = self.storage.list_all(
                            parent_id="abc*",
                            resource_name="c",
                            sorting=sort,
                            limit=limit,
                            pagination_rules=pagination,
                        )
                        total_objects = self.storage.count_all(parent_id="abc*", resource_name="c")
                        self.assertEqual(total_objects, len(real_objects))
                        objects.extend(page)
                        if len(objects) == total_objects:
                            break
                        # This should never happen normally, but lets
                        # us fail on an assert rather than an
                        # IndexError.
                        if not page:  # pragma: nocover
                            break
                        # Simulate paging though the objects as
                        # though following the logic in Resource._build_pagination_rules.
                        last_object = page[-1]
                        order_field, order_direction = order
                        pagination_direction = GT if order_direction == 1 else LT
                        threshhold_field = last_object[order_field]
                        threshhold_lm = last_object["last_modified"]
                        pagination = [
                            [
                                Filter(order_field, threshhold_field, utils.COMPARISON.EQ),
                                Filter("last_modified", threshhold_lm, utils.COMPARISON.LT),
                            ],
                            [Filter(order_field, threshhold_field, pagination_direction)],
                        ]

                    self.assertEqual(
                        sort_by_secret_data(real_objects), sort_by_secret_data(objects)
                    )

    def test_pagination_rules_are_confined_by_parent(self):
        intermediate_ts = None
        for i in range(4):
            r = self.create_object({"foo": i}, parent_id="/a")
            if i == 3:
                intermediate_ts = r["last_modified"]
        for i in range(4):
            self.create_object({"foo": i}, parent_id="/b")

        sort = [Sort("foo", -1), Sort("last_modified", -1)]
        pagination_rules = [
            [Filter("foo", 1, utils.COMPARISON.GT)],
            [Filter("last_modified", intermediate_ts, utils.COMPARISON.GT)],
        ]
        page = self.storage.list_all(
            resource_name="test",
            parent_id="/a",
            sorting=sort,
            limit=10,
            pagination_rules=pagination_rules,
        )
        self.assertEqual(len(page), 2)

    def test_delete_all_supports_pagination_rules(self):
        for i in range(6):
            self.create_object({"foo": i})

        pagination_rules = [[Filter("foo", 3, utils.COMPARISON.GT)]]
        deleted = self.storage.delete_all(
            limit=4, pagination_rules=pagination_rules, **self.storage_kw
        )
        self.assertEqual(len(deleted), 2)


class ParentObjectAccessTest:
    def test_parent_cannot_access_other_parent_object(self):
        obj = self.create_object()
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.get,
            resource_name=self.storage_kw["resource_name"],
            parent_id=self.other_parent_id,
            object_id=obj["id"],
        )

    def test_parent_cannot_delete_other_parent_object(self):
        obj = self.create_object()
        self.assertRaises(
            exceptions.ObjectNotFoundError,
            self.storage.delete,
            resource_name=self.storage_kw["resource_name"],
            parent_id=self.other_parent_id,
            object_id=obj["id"],
        )

    def test_parent_cannot_update_other_parent_object(self):
        obj = self.create_object()

        new_object = {"another": "object"}
        kw = {**self.storage_kw, "parent_id": self.other_parent_id}
        self.storage.update(object_id=obj["id"], obj=new_object, **kw)

        not_updated = self.storage.get(object_id=obj["id"], **self.storage_kw)
        self.assertNotIn("another", not_updated)


class SerializationTest:
    def test_create_bytes_raises(self):
        data = {"steak": "haché".encode(encoding="utf-8")}
        self.assertIsInstance(data["steak"], bytes)
        self.assertRaises(TypeError, self.create_object, data)

    def test_update_bytes_raises(self):
        obj = self.create_object()

        new_object = {"steak": "haché".encode(encoding="utf-8")}
        self.assertIsInstance(new_object["steak"], bytes)

        self.assertRaises(
            TypeError, self.storage.update, object_id=obj["id"], obj=new_object, **self.storage_kw
        )


class DeprecatedCoreNotionsTest:
    def setUp(self):
        super().setUp()
        patch = mock.patch("warnings.warn")
        self.mocked_warnings = patch.start()

    def test_deprecated_collection_timestamp(self):
        self.storage.collection_timestamp(collection_id="test", parent_id="")
        message = "`collection_timestamp()` is deprecated, use `resource_timestamp()` instead."
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_create_deprecated_kwargs(self):
        self.storage.create(record={}, collection_id="test", parent_id="")

        message = "Storage.create parameter 'record' is deprecated, use 'obj' instead"
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_get_deprecated_kwargs(self):
        self.storage.create(obj={"id": "abc"}, resource_name="test", parent_id="")

        self.storage.get(object_id="abc", collection_id="test", parent_id="")

        message = (
            "Storage.get parameter 'collection_id' is deprecated, use 'resource_name' instead"
        )
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_update_deprecated_kwargs(self):
        self.storage.update(object_id="abc", record={}, collection_id="test", parent_id="")

        message = "Storage.update parameter 'record' is deprecated, use 'obj' instead"
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_delete_deprecated_kwargs(self):
        self.storage.create(obj={"id": "abc"}, resource_name="test", parent_id="")

        self.storage.delete(object_id="abc", collection_id="test", parent_id="")

        message = (
            "Storage.delete parameter 'collection_id' is deprecated, use 'resource_name' instead"
        )
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_delete_all_deprecated_kwargs(self):
        self.storage.delete_all(collection_id="test", parent_id="")

        message = "Storage.delete_all parameter 'collection_id' is deprecated, use 'resource_name' instead"
        self.mocked_warnings.assert_called_with(message, DeprecationWarning)

    def test_get_all_deprecated_kwargs(self):
        r = self.storage.create(obj={"id": "abc"}, resource_name="test", parent_id="")

        records, count = self.storage.get_all(collection_id="test", parent_id="")

        message = "Use either self.list_all() or self.count_all()"
        self.mocked_warnings.assert_any_call(message, DeprecationWarning)
        # Check that proper `resource_name` was used (instead of `collection_id`)
        assert records == [r]
        assert count == 1


class StorageTest(
    ThreadMixin,
    TimestampsTest,
    DeletedObjectsTest,
    ParentObjectAccessTest,
    SerializationTest,
    DeprecatedCoreNotionsTest,
    BaseTestStorage,
):
    """Compound of all storage tests."""

    pass
