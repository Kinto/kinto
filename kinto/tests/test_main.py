try:
    import builtins
    builtins_name = 'builtins'
except ImportError:
    import __builtin__ as builtins
    builtins_name = '__builtin__'

import mock
import os
import pytest
import sys
import unittest

from six import StringIO

from kinto.__main__ import main


class TestMain(unittest.TestCase):
    def tearDown(self):
        try:
            os.remove('/tmp/kinto.ini')
        except OSError:
            pass

    def test_cli_init_generate_configuration(self):
        res = main(['--ini', '/tmp/kinto.ini', '--backend', 'memory', 'init'])
        assert res == 0
        assert os.path.exists('/tmp/kinto.ini')

    def test_cli_init_returns_if_file_exists(self):
        with open('/tmp/kinto.ini', 'w') as f:
            f.write("exists")
        with mock.patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            res = main(['--ini', '/tmp/kinto.ini',
                        '--backend', 'memory', 'init'])
            assert res == 1
            content = mock_stderr.getvalue()
            assert '/tmp/kinto.ini already exists.' in content

    def test_cli_init_ask_for_backend_if_not_specified(self):
        with mock.patch("kinto.__main__.input", create=True, return_value="2"):
            res = main(['--ini', '/tmp/kinto.ini', 'init'])
            assert res == 0

    def test_cli_init_ask_until_backend_is_valid(self):
        with mock.patch("kinto.__main__.input", create=True,
                        side_effect=["10", "2"]):
            res = main(['--ini', '/tmp/kinto.ini', 'init'])
            assert res == 0
            with open('/tmp/kinto.ini') as f:
                content = f.read()
            assert 'redis' in content

    def test_fails_if_not_enough_args(self):
        with mock.patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as excinfo:
                main(['--ini', '/tmp/kinto.ini'])
            assert 'INI_FILE' in mock_stderr.getvalue()
            assert excinfo.value.code == 2

    def test_cli_init_install_postgresql_dependencies_if_needed(self):
        realimport = builtins.__import__

        def myimport(name, *args, **kwargs):
            if name == 'psycopg2':
                raise ImportError()
            else:
                return realimport(name, *args, **kwargs)

        with mock.patch('{}.__import__'.format(builtins_name),
                        side_effect=myimport):
            with mock.patch('pip.main', return_value=None) as mocked_pip:
                with mock.patch("kinto.__main__.input", create=True,
                                return_value="1"):
                    res = main(['--ini', '/tmp/kinto.ini', 'init'])
                    assert res == 0
                    assert mocked_pip.call_count == 1

    def test_main_takes_sys_argv_by_default(self):
        testargs = ["prog", "--ini", "/tmp/kinto.ini",
                    '--backend', 'memory', 'init']
        with mock.patch.object(sys, 'argv', testargs):
            main()

        with open('/tmp/kinto.ini') as f:
            content = f.read()
        assert 'memory' in content

    def test_cli_migrate_command_runs_init_schema(self):
        with mock.patch('kinto.__main__.cliquet.init_schema') as mocked_init:
            res = main(['--ini', '/tmp/kinto.ini',
                        '--backend', 'memory', 'init'])
            assert res == 0
            res = main(['--ini', '/tmp/kinto.ini', 'migrate'])
            assert res == 0
            assert mocked_init.call_count == 1

    def test_cli_start_runs_pserve(self):
        with mock.patch('kinto.__main__.pserve.main') as mocked_pserve:
            res = main(['--ini', '/tmp/kinto.ini',
                        '--backend', 'memory', 'init'])
            assert res == 0
            res = main(['--ini', '/tmp/kinto.ini', 'start'])
            assert res == 0
            assert mocked_pserve.call_count == 1

    def test_cli_start_with_reload_runs_pserve_with_reload(self):
        with mock.patch('kinto.__main__.pserve.main') as mocked_pserve:
            res = main(['--ini', '/tmp/kinto.ini',
                        '--backend', 'memory', 'init'])
            assert res == 0
            res = main(['--ini', '/tmp/kinto.ini', 'start', '--reload'])
            assert res == 0
            assert mocked_pserve.call_count == 1
            assert '--reload' in mocked_pserve.call_args[0][0]
