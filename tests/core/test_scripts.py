import unittest
from unittest import mock

from kinto.core import scripts
from kinto.core.storage.postgresql import PostgreSQLPluginMigration
from kinto.core.storage.postgresql import Storage as PostgreSQLStorage


class _FakePluginMigration(PostgreSQLPluginMigration):
    name = "my_plugin"
    schema_version = 1
    schema_file = "/fake/schema.sql"
    migrations_directory = "/fake/migrations"


class InitSchemaTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()
        self.registry.storage = mock.MagicMock()
        self.registry.storage.__class__ = PostgreSQLStorage

    def test_migrate_calls_initialize_schema_on_backends(self):
        scripts.migrate({"registry": self.registry})
        self.assertTrue(self.registry.storage.initialize_schema.called)
        self.assertTrue(self.registry.cache.initialize_schema.called)
        self.assertTrue(self.registry.permission.initialize_schema.called)

    def test_migrate_skips_missing_backends(self):
        class FakeRegistry:
            settings = dict()
            storage = mock.MagicMock(spec=PostgreSQLStorage)

            def getUtilitiesFor(self, iface):
                return []

        registry = FakeRegistry()
        scripts.migrate({"registry": registry})
        self.assertTrue(registry.storage.initialize_schema.called)

    def test_migrate_runs_plugin_migrations(self):
        plugin_migration = _FakePluginMigration()
        self.registry.getUtilitiesFor.return_value = [("my_plugin", plugin_migration)]
        scripts.migrate({"registry": self.registry})
        assert plugin_migration.client is self.registry.storage.client

    def test_migrate_runs_plugin_migrations_dry_run(self):
        plugin_migration = _FakePluginMigration()
        with mock.patch.object(plugin_migration, "initialize_schema") as m:
            self.registry.getUtilitiesFor.return_value = [("my_plugin", plugin_migration)]
            scripts.migrate({"registry": self.registry}, dry_run=True)
        m.assert_called_once_with(self.registry.storage.client, dry_run=True)

    def test_migrate_skips_plugins_with_no_migrations(self):
        self.registry.getUtilitiesFor.return_value = []
        scripts.migrate({"registry": self.registry})

    def test_migrate_skips_plugin_when_storage_is_not_postgresql(self):
        self.registry.storage = mock.MagicMock()  # not a PostgreSQLStorage
        plugin_migration = _FakePluginMigration()
        with mock.patch.object(plugin_migration, "initialize_schema") as m:
            self.registry.getUtilitiesFor.return_value = [("my_plugin", plugin_migration)]
            scripts.migrate({"registry": self.registry})
        m.assert_not_called()

    def test_migrate_warns_on_unsupported_migration_type(self):
        plugin_migration = mock.MagicMock()  # not a PostgreSQLPluginMigration
        self.registry.getUtilitiesFor.return_value = [("my_plugin", plugin_migration)]
        with mock.patch("kinto.core.scripts.logger") as mocked_logger:
            scripts.migrate({"registry": self.registry})
        mocked_logger.warning.assert_any_call(
            "Migration has specific type %r for plugin %r.", type(plugin_migration), "my_plugin"
        )

    def test_migrate_in_read_only_display_an_error(self):
        with mock.patch("kinto.core.scripts.logger") as mocked:
            self.registry.settings = {"readonly": "true"}
            scripts.migrate({"registry": self.registry})
            mocked.error.assert_any_call(
                "Cannot migrate the storage backend while in readonly mode."
            )
            mocked.error.assert_any_call(
                "Cannot migrate the permission backend while in readonly mode."
            )

    def test_migrate_in_dry_run_mode(self):
        scripts.migrate({"registry": self.registry}, dry_run=True)
        reg = self.registry
        reg.storage.initialize_schema.assert_called_with(dry_run=True)
        reg.cache.initialize_schema.assert_called_with(dry_run=True)
        reg.permission.initialize_schema.assert_called_with(dry_run=True)

    def test_flush_cache_clear_the_cache_backend(self):
        scripts.flush_cache({"registry": self.registry})
        reg = self.registry
        reg.cache.flush.assert_called_with()


class PurgeDeletedTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()

    def test_purge_deleted(self):
        code = scripts.purge_deleted(
            {"registry": self.registry}, resource_names=["A", "B"], max_retained=42
        )
        assert code == 0
        self.registry.storage.purge_deleted.assert_any_call(
            parent_id="*", resource_name="A", max_retained=42, force_commit=True
        )
        self.registry.storage.purge_deleted.assert_any_call(
            parent_id="*", resource_name="B", max_retained=42, force_commit=True
        )
