from unittest import mock

import pytest

from kinto.core import DEFAULT_SETTINGS
from kinto.core.utils import COMPARISON, sqlalchemy
from kinto.core.storage import generators, memory, postgresql, exceptions, StorageBase
from kinto.core.storage import Filter, Sort, MISSING
from kinto.core.storage.testing import StorageTest
from kinto.core.storage.utils import paginated
from kinto.core.testing import unittest, skip_if_no_postgresql


class GeneratorTest(unittest.TestCase):
    def test_generic_has_mandatory_override(self):
        self.assertRaises(NotImplementedError, generators.Generator)

    def test_id_generator_must_respect_storage_backends(self):
        class Dumb(generators.Generator):
            def __call__(self):
                return "*" * 80

        self.assertRaises(ValueError, Dumb)

    def test_default_generator_allow_underscores_dash_alphabet(self):
        class Dumb(generators.Generator):
            def __call__(self):
                return "1234"

        generator = Dumb()
        self.assertTrue(generator.match("1_2_3-abc"))
        self.assertTrue(generator.match("abc_123"))
        self.assertFalse(generator.match("-1_2_3-abc"))
        self.assertFalse(generator.match("_1_2_3-abc"))

    def test_uuid_generator_pattern_allows_uuid_only(self):
        invalid_uuid = "XXX-00000000-0000-5000-a000-000000000000"
        generator = generators.UUID4()
        self.assertFalse(generator.match(invalid_uuid))

    def test_uuid_generator_pattern_is_not_restricted_to_uuid4(self):
        generator = generators.UUID4()
        valid_uuid = "fd800e8d-e8e9-3cac-f502-816cbed9bb6c"
        self.assertTrue(generator.match(valid_uuid))
        invalid_uuid4 = "00000000-0000-5000-a000-000000000000"
        self.assertTrue(generator.match(invalid_uuid4))
        invalid_uuid4 = "00000000-0000-4000-e000-000000000000"
        self.assertTrue(generator.match(invalid_uuid4))


class StorageBaseTest(unittest.TestCase):
    def setUp(self):
        self.storage = StorageBase()

    def test_mandatory_overrides(self):
        calls = [
            (self.storage.initialize_schema,),
            (self.storage.flush,),
            (self.storage.resource_timestamp, "", ""),
            (self.storage.create, "", "", {}),
            (self.storage.get, "", "", ""),
            (self.storage.update, "", "", "", {}),
            (self.storage.delete, "", "", ""),
            (self.storage.delete_all, "", ""),
            (self.storage.purge_deleted, "", ""),
            (self.storage.list_all, "", ""),
            (self.storage.count_all, "", ""),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)

    def test_backend_error_message_provides_given_message_if_defined(self):
        error = exceptions.BackendError(message="Connection Error")
        self.assertEqual(str(error), "Connection Error")

    def test_backenderror_message_default_to_original_exception_message(self):
        error = exceptions.BackendError(ValueError("Pool Error"))
        self.assertEqual(str(error), "ValueError: Pool Error")


class MemoryBasedStorageTest(unittest.TestCase):
    def test_backend_raise_not_implemented_error(self):
        storage = memory.MemoryBasedStorage()
        with pytest.raises(NotImplementedError):
            storage.bump_and_store_timestamp("object", "/school/foo/students/bar")


class MemoryStorageTest(StorageTest, unittest.TestCase):
    backend = memory
    settings = {"storage_strict_json": True}

    def setUp(self):
        super().setUp()
        self.client_error_patcher = mock.patch.object(
            self.storage,
            "bump_and_store_timestamp",
            side_effect=exceptions.BackendError("Segmentation fault."),
        )

    def test_backend_error_provides_original_exception(self):
        pass

    def test_raises_backend_error_if_error_occurs_on_client(self):
        pass

    def test_backend_error_is_raised_anywhere(self):
        pass

    def test_backenderror_message_default_to_original_exception_message(self):
        pass

    def test_ping_logs_error_if_unavailable(self):
        pass


class LenientMemoryStorageTest(MemoryStorageTest):
    settings = {"storage_strict_json": False}

    def test_create_bytes_raises(self):
        data = {"steak": "haché".encode(encoding="utf-8")}
        self.assertIsInstance(data["steak"], bytes)
        self.assertIsNotNone(self.create_object(data))

    def test_update_bytes_raises(self):
        obj = self.create_object()

        new_object = {"steak": "haché".encode(encoding="utf-8")}
        self.assertIsInstance(new_object["steak"], bytes)

        self.assertIsNotNone(
            self.storage.update(object_id=obj["id"], obj=new_object, **self.storage_kw)
        )


@skip_if_no_postgresql
class PostgreSQLStorageTest(StorageTest, unittest.TestCase):
    backend = postgresql
    settings = {
        "storage_max_fetch_size": 10000,
        "storage_backend": "kinto.core.storage.postgresql",
        "storage_poolclass": "sqlalchemy.pool.StaticPool",
        "storage_url": "postgresql://postgres:postgres@localhost:5432/testdb",
        "storage_strict_json": True,
    }

    def setUp(self):
        super().setUp()
        self.client_error_patcher = mock.patch.object(
            self.storage.client, "session_factory", side_effect=sqlalchemy.exc.SQLAlchemyError
        )

    def test_number_of_fetched_objects_can_be_limited_in_settings(self):
        for i in range(4):
            self.create_object({"phone": "tel-{}".format(i)})

        results = self.storage.list_all(**self.storage_kw)
        self.assertEqual(len(results), 4)

        settings = {**self.settings, "storage_max_fetch_size": 2}
        config = self._get_config(settings=settings)
        limited = self.backend.load_from_config(config)

        results = limited.list_all(**self.storage_kw)
        self.assertEqual(len(results), 2)
        count = limited.count_all(**self.storage_kw)
        self.assertEqual(count, 4)

    def test_number_of_fetched_objects_is_per_page(self):
        for i in range(10):
            self.create_object({"number": i})

        settings = {**self.settings, "storage_max_fetch_size": 2}
        config = self._get_config(settings=settings)
        backend = self.backend.load_from_config(config)

        results = backend.list_all(
            pagination_rules=[[Filter("number", 1, COMPARISON.GT)]], **self.storage_kw
        )
        self.assertEqual(len(results), 2)
        count = backend.count_all(**self.storage_kw)
        self.assertEqual(count, 10)

    def test_connection_is_rolledback_if_error_occurs(self):
        with self.storage.client.connect() as conn:
            query = "DELETE FROM objects WHERE resource_name = 'genre';"
            conn.execute(query)

        try:
            with self.storage.client.connect() as conn:
                query = """
                INSERT INTO objects VALUES ('rock-and-roll', 'music', 'genre', NOW(), '{}', FALSE);
                """
                conn.execute(query)
                conn.commit()

                query = """
                INSERT INTO objects VALUES ('jazz', 'music', 'genre', NOW(), '{}', FALSE);
                """
                conn.execute(query)

                raise sqlalchemy.exc.TimeoutError()
        except exceptions.BackendError:
            pass

        with self.storage.client.connect() as conn:
            query = "SELECT COUNT(*) FROM objects WHERE resource_name = 'genre';"
            result = conn.execute(query)
            self.assertEqual(result.fetchone()[0], 1)

    def test_pool_object_is_shared_among_backend_instances(self):
        config = self._get_config()
        storage1 = self.backend.load_from_config(config)
        storage2 = self.backend.load_from_config(config)
        self.assertEqual(id(storage1.client), id(storage2.client))

    def test_warns_if_configured_pool_size_differs_for_same_backend_type(self):
        self.backend.load_from_config(self._get_config())
        settings = {**self.settings, "storage_pool_size": 1}
        msg = "Reuse existing PostgreSQL connection. Parameters storage_* " "will be ignored."
        with mock.patch("kinto.core.storage.postgresql.client." "warnings.warn") as mocked:
            self.backend.load_from_config(self._get_config(settings=settings))
            mocked.assert_any_call(msg)

    def test_list_all_raises_if_missing_on_strange_query(self):
        with self.assertRaises(ValueError):
            self.storage.list_all(
                "some-resource", "some-parent", filters=[Filter("author", MISSING, COMPARISON.HAS)]
            )

    def test_integrity_error_rollsback_transaction(self):
        client = postgresql.create_from_config(
            self._get_config(), prefix="storage_", with_transaction=False
        )
        with self.assertRaises(exceptions.IntegrityError):
            with client.connect() as conn:
                # Make some change in a table.
                conn.execute(
                    """
                INSERT INTO objects
                VALUES ('rock-and-roll', 'music', 'genre', NOW(), '{}', FALSE);
                """
                )
                # Go into a failing integrity constraint.
                query = "INSERT INTO timestamps VALUES ('a', 'b', NOW());"
                conn.execute(query)
                conn.execute(query)
                conn.commit()
                conn.close()

        # Check that change in the above table was rolledback.
        with client.connect() as conn:
            result = conn.execute(
                """
            SELECT FROM objects
             WHERE parent_id = 'music'
               AND resource_name = 'genre';
            """
            )
        self.assertEqual(result.rowcount, 0)

    def test_conflicts_handled_correctly(self):
        config = self._get_config()
        storage = self.backend.load_from_config(config)
        storage.create(resource_name="genre", parent_id="music", obj={"id": "rock-and-roll"})

        def object_not_found(*args, **kwargs):
            raise exceptions.ObjectNotFoundError()

        with mock.patch.object(storage, "get", side_effect=object_not_found):
            with self.assertRaises(exceptions.UnicityError):
                storage.create(
                    resource_name="genre", parent_id="music", obj={"id": "rock-and-roll"}
                )

    def test_supports_null_pool(self):
        settings = {
            **DEFAULT_SETTINGS,
            **self.settings,
            "storage_poolclass": "sqlalchemy.pool.NullPool",
        }
        config = self._get_config(settings=settings)
        self.backend.load_from_config(config)  # does not raise


class PaginatedTest(unittest.TestCase):
    def setUp(self):
        self.storage = mock.Mock()
        self.sample_objects = [
            {"id": "object-01", "flavor": "strawberry"},
            {"id": "object-02", "flavor": "banana"},
            {"id": "object-03", "flavor": "mint"},
            {"id": "object-04", "flavor": "plain"},
            {"id": "object-05", "flavor": "peanut"},
        ]

        def sample_objects_side_effect(*args, **kwargs):
            return self.sample_objects

        self.storage.list_all.side_effect = sample_objects_side_effect

    def test_paginated_passes_sort(self):
        i = paginated(self.storage, sorting=[Sort("id", -1)])
        next(i)  # make the generator do anything
        self.storage.list_all.assert_called_with(
            sorting=[Sort("id", -1)], limit=25, pagination_rules=None
        )

    def test_paginated_passes_batch_size(self):
        i = paginated(self.storage, sorting=[Sort("id", -1)], batch_size=17)
        next(i)  # make the generator do anything
        self.storage.list_all.assert_called_with(
            sorting=[Sort("id", -1)], limit=17, pagination_rules=None
        )

    def test_paginated_yields_objects(self):
        iter = paginated(self.storage, sorting=[Sort("id", -1)])
        assert next(iter) == {"id": "object-01", "flavor": "strawberry"}

    def test_paginated_fetches_next_page(self):
        objects = self.sample_objects
        objects.reverse()

        def list_all_mock(*args, **kwargs):
            this_objects = objects[:3]
            del objects[:3]
            return this_objects

        self.storage.list_all.side_effect = list_all_mock

        list(paginated(self.storage, sorting=[Sort("id", -1)]))
        assert self.storage.list_all.call_args_list == [
            mock.call(sorting=[Sort("id", -1)], limit=25, pagination_rules=None),
            mock.call(
                sorting=[Sort("id", -1)],
                limit=25,
                pagination_rules=[[Filter("id", "object-03", COMPARISON.LT)]],
            ),
            mock.call(
                sorting=[Sort("id", -1)],
                limit=25,
                pagination_rules=[[Filter("id", "object-01", COMPARISON.LT)]],
            ),
        ]
