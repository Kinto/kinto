import os
import unittest
from unittest import mock

from kinto.core.storage.postgresql import PostgreSQLPluginMigration


class PostgreSQLPluginMigrationTest(unittest.TestCase):
    def setUp(self):
        self.client = mock.MagicMock()
        here = os.path.dirname(__file__)

        class MyMigration(PostgreSQLPluginMigration):
            name = "test_plugin"
            schema_version = 2
            schema_file = os.path.join(here, "migrations", "plugin_schema.sql")
            migrations_directory = os.path.join(here, "migrations")

        self.migration = MyMigration()
        self.migration.client = self.client

    def _mock_version(self, version):
        row = mock.MagicMock()
        row.version = str(version) if version is not None else None
        result = mock.MagicMock()
        result.fetchone.return_value = None if version is None else row
        self.client.connect.return_value.__enter__.return_value.execute.return_value = result

    def test_get_installed_version_returns_integer(self):
        self._mock_version(2)
        assert self.migration.get_installed_version() == 2

    def test_get_installed_version_returns_1_when_no_row(self):
        self._mock_version(None)
        assert self.migration.get_installed_version() == 1

    def test_initialize_schema_sets_client_and_delegates(self):
        with mock.patch.object(self.migration, "create_or_migrate_schema") as m:
            self.migration.initialize_schema(self.client, dry_run=True)
        assert self.migration.client is self.client
        m.assert_called_once_with(True)
