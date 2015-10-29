import mock

from cliquet.scripts import cliquet as cliquet_script

from .support import unittest


class InitSchemaTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()

    def run_command(self, command):
        with mock.patch('cliquet.scripts.cliquet.bootstrap') as mocked:
            mocked.return_value = {'registry': self.registry}
            with mock.patch('cliquet.scripts.cliquet.sys') as sys_mocked:
                sys_mocked.argv = ['prog', '--ini', 'foo.ini', command]
                cliquet_script.main()

    def test_deprecated_init_command_is_supported(self):
        self.run_command('init')
        self.assertTrue(self.registry.storage.initialize_schema.called)
        self.assertTrue(self.registry.cache.initialize_schema.called)
        self.assertTrue(self.registry.permission.initialize_schema.called)

    def test_migrate_calls_initialize_schema_on_backends(self):
        self.run_command('migrate')
        self.assertTrue(self.registry.storage.initialize_schema.called)
        self.assertTrue(self.registry.cache.initialize_schema.called)
        self.assertTrue(self.registry.permission.initialize_schema.called)

    def test_migrate_in_read_only_display_warnings(self):
        with mock.patch('cliquet.scripts.cliquet.warnings.warn') as mocked:
            self.registry.settings = {'readonly': 'true'}
            self.run_command('migrate')
            mocked.assert_any_call('Cannot migrate the storage backend '
                                   'while in readonly mode.')
            mocked.assert_any_call('Cannot migrate the permission backend '
                                   'while in readonly mode.')
