import mock

from cliquet.scripts import cliquet as cliquet_script

from .support import unittest


class InitSchemaTest(unittest.TestCase):
    def test_init_schema_calls_initialize_schema_on_cache_and_storage(self):
        fakeregistry = mock.MagicMock()
        with mock.patch('cliquet.scripts.cliquet.bootstrap') as mocked:
            mocked.return_value = {'registry': fakeregistry}
            with mock.patch('cliquet.scripts.cliquet.sys') as sys_mocked:
                sys_mocked.argv = ['prog', '--ini', 'foo.ini', 'init']
                cliquet_script.main()
                self.assertTrue(fakeregistry.storage.initialize_schema.called)
                self.assertTrue(fakeregistry.cache.initialize_schema.called)
