import mock

from kinto.core import scripts

from .support import unittest


class InitSchemaTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()

    def test_migrate_calls_initialize_schema_on_backends(self):
        scripts.migrate({'registry': self.registry})
        self.assertTrue(self.registry.storage.initialize_schema.called)
        self.assertTrue(self.registry.cache.initialize_schema.called)
        self.assertTrue(self.registry.permission.initialize_schema.called)

    def test_migrate_in_read_only_display_warnings(self):
        with mock.patch('kinto.core.scripts.warnings.warn') as mocked:
            self.registry.settings = {'readonly': 'true'}
            scripts.migrate({'registry': self.registry})
            mocked.assert_any_call('Cannot migrate the storage backend '
                                   'while in readonly mode.')
            mocked.assert_any_call('Cannot migrate the permission backend '
                                   'while in readonly mode.')
