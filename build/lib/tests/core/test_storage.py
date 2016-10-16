# -*- coding: utf-8 -*-

import mock

from kinto.core.utils import sqlalchemy
from kinto.core.storage import generators, memory, postgresql, exceptions, StorageBase
from kinto.core.testing import (unittest, skip_if_no_postgresql)
from kinto.core.storage.testing import StorageTest


class GeneratorTest(unittest.TestCase):
    def test_generic_has_mandatory_override(self):
        self.assertRaises(NotImplementedError, generators.Generator)

    def test_id_generator_must_respect_storage_backends(self):
        class Dumb(generators.Generator):
            def __call__(self):
                return '*' * 80

        self.assertRaises(AssertionError, Dumb)

    def test_default_generator_allow_underscores_dash_alphabet(self):
        class Dumb(generators.Generator):
            def __call__(self):
                return '1234'

        generator = Dumb()
        self.assertTrue(generator.match('1_2_3-abc'))
        self.assertTrue(generator.match('abc_123'))
        self.assertFalse(generator.match('-1_2_3-abc'))
        self.assertFalse(generator.match('_1_2_3-abc'))

    def test_uuid_generator_pattern_allows_uuid_only(self):
        invalid_uuid = 'XXX-00000000-0000-5000-a000-000000000000'
        generator = generators.UUID4()
        self.assertFalse(generator.match(invalid_uuid))

    def test_uuid_generator_pattern_is_not_restricted_to_uuid4(self):
        generator = generators.UUID4()
        valid_uuid = 'fd800e8d-e8e9-3cac-f502-816cbed9bb6c'
        self.assertTrue(generator.match(valid_uuid))
        invalid_uuid4 = '00000000-0000-5000-a000-000000000000'
        self.assertTrue(generator.match(invalid_uuid4))
        invalid_uuid4 = '00000000-0000-4000-e000-000000000000'
        self.assertTrue(generator.match(invalid_uuid4))


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
            (self.storage.purge_deleted, '', ''),
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


class MemoryStorageTest(StorageTest, unittest.TestCase):
    backend = memory

    def setUp(self):
        super(MemoryStorageTest, self).setUp()
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

    def test_ping_logs_error_if_unavailable(self):
        pass


@skip_if_no_postgresql
class PostgreSQLStorageTest(StorageTest, unittest.TestCase):
    backend = postgresql
    settings = {
        'storage_max_fetch_size': 10000,
        'storage_backend': 'kinto.core.storage.postgresql',
        'storage_poolclass': 'sqlalchemy.pool.StaticPool',
        'storage_url': 'postgres://postgres:postgres@localhost:5432/testdb',
    }

    def setUp(self):
        super(PostgreSQLStorageTest, self).setUp()
        self.client_error_patcher = mock.patch.object(
            self.storage.client,
            'session_factory',
            side_effect=sqlalchemy.exc.SQLAlchemyError)

    def test_number_of_fetched_records_can_be_limited_in_settings(self):
        for i in range(4):
            self.create_record({'phone': 'tel-%s' % i})

        results, count = self.storage.get_all(**self.storage_kw)
        self.assertEqual(len(results), 4)

        settings = self.settings.copy()
        settings['storage_max_fetch_size'] = 2
        config = self._get_config(settings=settings)
        limited = self.backend.load_from_config(config)

        results, count = limited.get_all(**self.storage_kw)
        self.assertEqual(len(results), 2)

    def test_connection_is_rolledback_if_error_occurs(self):
        with self.storage.client.connect() as conn:
            query = "DELETE FROM metadata WHERE name = 'roll';"
            conn.execute(query)

        try:
            with self.storage.client.connect() as conn:
                query = "INSERT INTO metadata VALUES ('roll', 'back');"
                conn.execute(query)
                conn.commit()

                query = "INSERT INTO metadata VALUES ('roll', 'rock');"
                conn.execute(query)

                raise sqlalchemy.exc.TimeoutError()
        except exceptions.BackendError:
            pass

        with self.storage.client.connect() as conn:
            query = "SELECT COUNT(*) FROM metadata WHERE name = 'roll';"
            result = conn.execute(query)
            self.assertEqual(result.fetchone()[0], 1)

    def test_pool_object_is_shared_among_backend_instances(self):
        config = self._get_config()
        storage1 = self.backend.load_from_config(config)
        storage2 = self.backend.load_from_config(config)
        self.assertEqual(id(storage1.client),
                         id(storage2.client))

    def test_warns_if_configured_pool_size_differs_for_same_backend_type(self):
        self.backend.load_from_config(self._get_config())
        settings = self.settings.copy()
        settings['storage_pool_size'] = 1
        msg = ('Reuse existing PostgreSQL connection. Parameters storage_* '
               'will be ignored.')
        with mock.patch('kinto.core.storage.postgresql.client.'
                        'warnings.warn') as mocked:
            self.backend.load_from_config(self._get_config(settings=settings))
            mocked.assert_any_call(msg)
