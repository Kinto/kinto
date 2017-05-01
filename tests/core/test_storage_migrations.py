import os
import unittest

import mock
from pyramid import testing

from kinto.core.cache import postgresql as postgresql_cache
from kinto.core.permission import postgresql as postgresql_permission
from kinto.core.storage import postgresql as postgresql_storage
from kinto.core.utils import json
from kinto.core.testing import skip_if_no_postgresql


@skip_if_no_postgresql
class PostgresqlStorageMigrationTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from kinto.core.utils import sqlalchemy
        if sqlalchemy is None:
            return

        from .test_storage import PostgreSQLStorageTest
        self.settings = {**PostgreSQLStorageTest.settings}
        self.config = testing.setUp()
        self.config.add_settings(self.settings)
        self.version = postgresql_storage.Storage.schema_version
        # Usual storage object to manipulate the storage.
        self.storage = postgresql_storage.load_from_config(self.config)

    def setUp(self):
        # Start empty.
        self._delete_everything()
        # Create schema in its last version
        self.storage.initialize_schema()
        # Patch to keep track of SQL files executed.
        self.sql_execute_patcher = mock.patch(
            'kinto.core.storage.postgresql.Storage._execute_sql_file')

    def tearDown(self):
        postgresql_storage.Storage.schema_version = self.version
        mock.patch.stopall()

    def _delete_everything(self):
        q = """
        DROP TABLE IF EXISTS records CASCADE;
        DROP TABLE IF EXISTS deleted CASCADE;
        DROP TABLE IF EXISTS metadata CASCADE;
        DROP FUNCTION IF EXISTS resource_timestamp(VARCHAR, VARCHAR);
        DROP FUNCTION IF EXISTS collection_timestamp(VARCHAR, VARCHAR);
        DROP FUNCTION IF EXISTS bump_timestamp();
        """
        with self.storage.client.connect() as conn:
            conn.execute(q)

    def test_does_not_execute_if_ran_with_dry(self):
        self._delete_everything()
        self.storage.initialize_schema(dry_run=True)
        query = """SELECT 1 FROM information_schema.tables
        WHERE table_name = 'records';"""
        with self.storage.client.connect(readonly=True) as conn:
            result = conn.execute(query)
        self.assertEqual(result.rowcount, 0)

    def test_schema_sets_the_current_version(self):
        version = self.storage._get_installed_version()
        self.assertEqual(version, self.version)

    def test_schema_is_not_recreated_from_scratch_if_already_exists(self):
        mocked = self.sql_execute_patcher.start()
        self.storage.initialize_schema()
        self.assertFalse(mocked.called)

    def test_schema_is_considered_first_version_if_no_version_detected(self):
        with self.storage.client.connect() as conn:
            q = "DELETE FROM metadata WHERE name = 'storage_schema_version';"
            conn.execute(q)

        mocked = self.sql_execute_patcher.start()
        postgresql_storage.Storage.schema_version = 2
        self.storage.initialize_schema()
        sql_called = mocked.call_args[0][0]
        self.assertIn('migrations/migration_001_002.sql', sql_called)

    def test_migration_file_is_executed_for_every_intermediary_version(self):
        postgresql_storage.Storage.schema_version = 6

        versions = [6, 5, 4, 3, 3]
        self.storage._get_installed_version = lambda: versions.pop()

        mocked = self.sql_execute_patcher.start()
        self.storage.initialize_schema()
        sql_called = mocked.call_args_list[-3][0][0]
        self.assertIn('migrations/migration_003_004.sql', sql_called)
        sql_called = mocked.call_args_list[-2][0][0]
        self.assertIn('migrations/migration_004_005.sql', sql_called)
        sql_called = mocked.call_args_list[-1][0][0]
        self.assertIn('migrations/migration_005_006.sql', sql_called)

    def test_migration_files_are_listed_if_ran_with_dry_run(self):
        postgresql_storage.Storage.schema_version = 6

        versions = [6, 5, 4, 3, 3]
        self.storage._get_installed_version = lambda: versions.pop()

        with mock.patch('kinto.core.storage.postgresql.logger') as mocked:
            self.storage.initialize_schema(dry_run=True)

        output = ''.join([repr(call) for call in mocked.info.call_args_list])
        self.assertIn('migrations/migration_003_004.sql', output)
        self.assertIn('migrations/migration_004_005.sql', output)
        self.assertIn('migrations/migration_005_006.sql', output)

    def test_migration_fails_if_intermediary_version_is_missing(self):
        with mock.patch.object(self.storage,
                               '_get_installed_version') as current:
            current.return_value = -1
            self.sql_execute_patcher.start()
            self.assertRaises(AssertionError, self.storage.initialize_schema)

    def test_every_available_migration(self):
        """Test every migration available in kinto.core code base since
        version 1.6.

        Records migration test is currently very naive, and should be
        elaborated along future migrations.
        """
        self._delete_everything()

        # Install old schema
        with self.storage.client.connect() as conn:
            here = os.path.abspath(os.path.dirname(__file__))
            filepath = 'schema/postgresql-storage-1.6.sql'
            with open(os.path.join(here, filepath)) as f:
                old_schema = f.read()
            conn.execute(old_schema)

        # Create a sample record using some code that is compatible with the
        # schema in place in cliquet 1.6.
        with self.storage.client.connect() as conn:
            before = {'drink': 'cacao'}
            query = """
            INSERT INTO records (user_id, resource_name, data)
            VALUES (:user_id, :resource_name, (:data)::JSON)
            RETURNING id, as_epoch(last_modified) AS last_modified;
            """
            placeholders = dict(user_id='jean-louis',
                                resource_name='test',
                                data=json.dumps(before))
            result = conn.execute(query, placeholders)
            inserted = result.fetchone()
            before['id'] = str(inserted['id'])
            before['last_modified'] = inserted['last_modified']

        # In cliquet 1.6, version = 1.
        version = self.storage._get_installed_version()
        self.assertEqual(version, 1)

        # Run every migrations available.
        self.storage.initialize_schema()

        # Version matches current one.
        version = self.storage._get_installed_version()
        self.assertEqual(version, self.version)

        # Check that previously created record is still here
        migrated, count = self.storage.get_all('test', 'jean-louis')
        self.assertEqual(migrated[0], before)

        # Check that new records can be created
        r = self.storage.create('test', ',jean-louis', {'drink': 'mate'})

        # And deleted
        self.storage.delete('test', ',jean-louis', r['id'])

    def test_every_available_migration_succeeds_if_tables_were_flushed(self):
        # During tests, tables can be flushed.
        self.storage.flush()
        self.storage.initialize_schema()
        # Version matches current one.
        version = self.storage._get_installed_version()
        self.assertEqual(version, self.version)

    def test_migration_12_clean_tombstones(self):
        self._delete_everything()
        postgresql_storage.Storage.schema_version = 11
        self.storage.initialize_schema()
        # Set the schema version back to 11 in the base as well
        with self.storage.client.connect() as conn:
            query = """
            UPDATE metadata SET value = '11'
            WHERE name = 'storage_schema_version';
            """
            conn.execute(query)
        r = self.storage.create('test', 'jean-louis', {'drink': 'mate'})
        self.storage.delete('test', 'jean-louis', r['id'])

        # Insert back the record without removing the tombstone.
        with self.storage.client.connect() as conn:
            query = """
            INSERT INTO records (id, parent_id, collection_id,
                                 data, last_modified)
            VALUES (:id, :parent_id, :collection_id,
                    (:data)::JSONB, from_epoch(:last_modified));
            """
            placeholders = dict(id=r['id'],
                                collection_id='test',
                                parent_id='jean-louis',
                                data=json.dumps({'drink': 'mate'}),
                                last_modified=1468400666777)
            conn.execute(query, placeholders)

        records, count = self.storage.get_all('test', 'jean-louis',
                                              include_deleted=True)
        # Check that we have the tombstone
        assert len(records) == 2
        assert count == 1

        # Execute the 011 to 012 migration
        postgresql_storage.Storage.schema_version = 12
        self.storage.initialize_schema()

        # Check that the rotted tombstone have been removed.
        records, count = self.storage.get_all('test', 'jean-louis',
                                              include_deleted=True)
        # Only the record remains.
        assert len(records) == 1
        assert count == 1


@skip_if_no_postgresql
class PostgresqlPermissionMigrationTest(unittest.TestCase):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        from kinto.core.utils import sqlalchemy
        if sqlalchemy is None:
            return

        from .test_permission import PostgreSQLPermissionTest
        settings = {**PostgreSQLPermissionTest.settings}
        config = testing.setUp()
        config.add_settings(settings)
        self.permission = postgresql_permission.load_from_config(config)

    def setUp(self):
        q = """
        DROP TABLE IF EXISTS access_control_entries CASCADE;
        DROP TABLE IF EXISTS user_principals CASCADE;
        """
        with self.permission.client.connect() as conn:
            conn.execute(q)

    def test_runs_initialize_schema_if_using_it_fails(self):
        self.permission.initialize_schema()
        query = """SELECT 1 FROM information_schema.tables
        WHERE table_name = 'user_principals';"""
        with self.permission.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            self.assertEqual(result.rowcount, 1)

    def test_does_not_execute_if_ran_with_dry(self):
        self.permission.initialize_schema(dry_run=True)
        query = """SELECT 1 FROM information_schema.tables
        WHERE table_name = 'user_principals';"""
        with self.permission.client.connect(readonly=True) as conn:
            result = conn.execute(query)
        self.assertEqual(result.rowcount, 0)


@skip_if_no_postgresql
class PostgresqlCacheMigrationTest(unittest.TestCase):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        from kinto.core.utils import sqlalchemy
        if sqlalchemy is None:
            return

        from .test_cache import PostgreSQLCacheTest
        settings = {**PostgreSQLCacheTest.settings}
        config = testing.setUp()
        config.add_settings(settings)
        self.cache = postgresql_cache.load_from_config(config)

    def setUp(self):
        q = """
        DROP TABLE IF EXISTS cache CASCADE;
        """
        with self.cache.client.connect() as conn:
            conn.execute(q)

    def test_runs_initialize_schema_if_using_it_fails(self):
        self.cache.initialize_schema()
        query = """SELECT 1 FROM information_schema.tables
        WHERE table_name = 'cache';"""
        with self.cache.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            self.assertEqual(result.rowcount, 1)

    def test_does_not_execute_if_ran_with_dry(self):
        self.cache.initialize_schema(dry_run=True)
        query = """SELECT 1 FROM information_schema.tables
        WHERE table_name = 'cache';"""
        with self.cache.client.connect(readonly=True) as conn:
            result = conn.execute(query)
        self.assertEqual(result.rowcount, 0)


class PostgresqlExceptionRaisedTest(unittest.TestCase):
    def setUp(self):
        self.sqlalchemy = postgresql_storage.client.sqlalchemy

    def tearDown(self):
        postgresql_storage.client.sqlalchemy = self.sqlalchemy

    def test_postgresql_usage_raise_an_error_if_postgresql_not_installed(self):
        postgresql_storage.client.sqlalchemy = None
        with self.assertRaises(ImportWarning):
            postgresql_storage.client.create_from_config(testing.setUp())
