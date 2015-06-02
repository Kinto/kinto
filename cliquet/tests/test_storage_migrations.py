import os

import mock

from cliquet.storage import postgresql
from cliquet.utils import json

from .support import unittest


class PostgresqlStorageMigrationTest(unittest.TestCase):
    def setUp(self):
        from .test_storage import PostgresqlStorageTest

        self.settings = PostgresqlStorageTest.settings.copy()
        self.config = mock.Mock(get_settings=mock.Mock(
            return_value=self.settings))

        self.version = postgresql.PostgreSQL.schema_version

        # Usual storage object to manipulate the storage.
        self.storage = postgresql.load_from_config(self.config)

        # Start empty.
        self._delete_everything()

        # Create schema in its last version
        self.storage = postgresql.load_from_config(self.config)
        self.storage.initialize_schema()

        # Patch to keep track of SQL files executed.
        self.sql_execute_patcher = mock.patch(
            'cliquet.storage.postgresql.PostgreSQL._execute_sql_file')

    def tearDown(self):
        postgresql.PostgreSQL.schema_version = self.version
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
        with self.storage.connect() as cursor:
            cursor.execute(q)

    def test_schema_sets_the_current_version(self):
        version = self.storage._get_installed_version()
        self.assertEqual(version, self.version)

    def test_schema_is_not_recreated_from_scratch_if_already_exists(self):
        mocked = self.sql_execute_patcher.start()
        self.storage.initialize_schema()
        self.assertFalse(mocked.called)

    def test_schema_is_considered_first_version_if_no_version_detected(self):
        with self.storage.connect() as cursor:
            q = "DELETE FROM metadata WHERE name = 'storage_schema_version';"
            cursor.execute(q)

        mocked = self.sql_execute_patcher.start()
        postgresql.PostgreSQL.schema_version = 2
        self.storage.initialize_schema()
        mocked.assert_any_call('migrations/migration_001_002.sql')

    def test_migration_file_is_executed_for_every_intermediary_version(self):
        postgresql.PostgreSQL.schema_version = 6

        versions = [6, 5, 4, 3, 3]
        self.storage._get_installed_version = lambda: versions.pop()

        mocked = self.sql_execute_patcher.start()
        self.storage.initialize_schema()
        mocked.assert_any_call('migrations/migration_003_004.sql')
        mocked.assert_any_call('migrations/migration_004_005.sql')
        mocked.assert_any_call('migrations/migration_005_006.sql')

    def test_migration_fails_if_intermediary_version_is_missing(self):
        with mock.patch.object(self.storage,
                               '_get_installed_version') as current:
            current.return_value = -1
            self.sql_execute_patcher.start()
            self.assertRaises(AssertionError, self.storage.initialize_schema)

    def test_every_available_migration(self):
        """Test every migration available in cliquet code base since
        version 1.6.

        Records migration test is currently very naive, and should be
        elaborated along future migrations.
        """
        self._delete_everything()

        # Install old schema
        with self.storage.connect() as cursor:
            here = os.path.abspath(os.path.dirname(__file__))
            filepath = 'schema/postgresql-storage-1.6.sql'
            old_schema = open(os.path.join(here, filepath)).read()
            cursor.execute(old_schema)

        # Create a sample record using some code that is compatible with the
        # schema in place in cliquet 1.6.
        with self.storage.connect() as cursor:
            before = {'drink': 'cacao'}
            query = """
            INSERT INTO records (user_id, resource_name, data)
            VALUES (%(user_id)s, %(resource_name)s, %(data)s::JSON)
            RETURNING id, as_epoch(last_modified) AS last_modified;
            """
            placeholders = dict(user_id='jean-louis',
                                resource_name='test',
                                data=json.dumps(before))
            cursor.execute(query, placeholders)
            inserted = cursor.fetchone()
            before['id'] = inserted['id']
            before['last_modified'] = inserted['last_modified']

        # In cliquet 1.6, version = 1.
        version = self.storage._get_installed_version()
        self.assertEqual(version, 1)

        # Run every migrations available.
        self.storage.initialize_schema()

        # Version matches current one.
        version = self.storage._get_installed_version()
        self.assertEqual(version, self.version)

        migrated, count = self.storage.get_all('test', 'jean-louis')
        self.assertEqual(migrated[0], before)

    def test_every_available_migration_succeeds_if_tables_were_flushed(self):
        # During tests, tables can be flushed.
        self.storage.flush()
        self.storage.initialize_schema()
        # Version matches current one.
        version = self.storage._get_installed_version()
        self.assertEqual(version, self.version)
