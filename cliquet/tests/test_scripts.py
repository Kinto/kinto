import mock

from cliquet.scripts import init_schema

from .support import unittest


class InitSchemaTest(unittest.TestCase):
    def test_returns_if_no_enough_arguments(self):
        with mock.patch('cliquet.scripts.init_schema.sys') as sys_mocked:
            sys_mocked.argv = ['prog']
            self.assertEqual(init_schema.main(), 2)

    def test_init_schema_calls_initialize_schema_on_cache_and_storage(self):
        fakeregistry = mock.MagicMock()
        with mock.patch('cliquet.scripts.init_schema.bootstrap') as mocked:
            mocked.return_value = {'registry': fakeregistry}
            with mock.patch('cliquet.scripts.init_schema.sys') as sys_mocked:
                sys_mocked.argv = ['prog', 'foo.ini']
                init_schema.main()
                self.assertTrue(fakeregistry.storage.initialize_schema.called)
                self.assertTrue(fakeregistry.cache.initialize_schema.called)
