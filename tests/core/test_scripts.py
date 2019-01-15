import unittest
from unittest import mock

from kinto.core import scripts


class InitSchemaTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()

    def test_migrate_calls_initialize_schema_on_backends(self):
        scripts.migrate({"registry": self.registry})
        self.assertTrue(self.registry.storage.initialize_schema.called)
        self.assertTrue(self.registry.cache.initialize_schema.called)
        self.assertTrue(self.registry.permission.initialize_schema.called)

    def test_migrate_skips_missing_backends(self):
        class FakeRegistry:
            settings = dict()
            storage = mock.MagicMock()

        registry = FakeRegistry()
        scripts.migrate({"registry": registry})
        self.assertTrue(registry.storage.initialize_schema.called)

    def test_migrate_in_read_only_display_an_error(self):
        with mock.patch("kinto.core.scripts.logger") as mocked:
            self.registry.settings = {"readonly": "true"}
            scripts.migrate({"registry": self.registry})
            mocked.error.assert_any_call(
                "Cannot migrate the storage backend " "while in readonly mode."
            )
            mocked.error.assert_any_call(
                "Cannot migrate the permission " "backend while in readonly mode."
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
