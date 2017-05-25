import builtins
import logging
import mock
import os
import pytest
import sys
import tempfile
import unittest

from io import StringIO

from kinto import __version__ as kinto_version
from kinto.__main__ import main, DEFAULT_LOG_FORMAT

_, TEMP_KINTO_INI = tempfile.mkstemp(prefix='kinto_config', suffix='.ini')


class TestMain(unittest.TestCase):
    def setUp(self):
        try:
            os.remove(TEMP_KINTO_INI)
        except OSError:
            pass

    def test_cli_init_generates_configuration(self):
        res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
        assert res == 0
        assert os.path.exists(TEMP_KINTO_INI)

    def test_cli_init_returns_if_file_exists(self):
        with open(TEMP_KINTO_INI, 'w') as f:
            f.write("exists")
        with mock.patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 1
            content = mock_stderr.getvalue()
            assert '{} already exists.'.format(TEMP_KINTO_INI) in content

    def test_cli_init_asks_for_backend_if_not_specified(self):
        with mock.patch("kinto.__main__.input", create=True, return_value="2"):
            res = main(['init', '--ini', TEMP_KINTO_INI])
            assert res == 0
        with open(TEMP_KINTO_INI) as f:
            content = f.read()
        assert 'redis' in content

    def test_cli_init_asks_until_backend_is_valid(self):
        with mock.patch("kinto.__main__.input", create=True, side_effect=["10", "2"]):
            res = main(['init', '--ini', TEMP_KINTO_INI])
            assert res == 0
            with open(TEMP_KINTO_INI) as f:
                content = f.read()
            assert 'redis' in content

    def test_fails_if_not_enough_args(self):
        with mock.patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as excinfo:
                main([])
            assert 'arguments are required: subcommand' in mock_stderr.getvalue()
            assert excinfo.value.code == 2

    def test_cli_init_installs_postgresql_dependencies_if_needed(self):
        realimport = builtins.__import__

        def psycopg2_missing(name, *args, **kwargs):
            if name == 'psycopg2':
                raise ImportError()
            else:
                return realimport(name, *args, **kwargs)

        with mock.patch('builtins.__import__', side_effect=psycopg2_missing):
            with mock.patch('pip.main', return_value=None) as mocked_pip:
                with mock.patch("kinto.__main__.input", create=True, return_value="1"):
                    res = main(['init', '--ini', TEMP_KINTO_INI])
                    assert res == 0
                    assert mocked_pip.call_count == 1

    def test_cli_init_installs_redis_dependencies_if_needed(self):
        realimport = builtins.__import__

        def redis_missing(name, *args, **kwargs):
            if name == 'kinto_redis':
                raise ImportError()
            else:
                return realimport(name, *args, **kwargs)

        with mock.patch('builtins.__import__', side_effect=redis_missing):
            with mock.patch('pip.main', return_value=None) as mocked_pip:
                with mock.patch("kinto.__main__.input", create=True, return_value="2"):
                    res = main(['init', '--ini', TEMP_KINTO_INI])
                    assert res == 0
                    assert mocked_pip.call_count == 1

    def test_main_takes_sys_argv_by_default(self):
        testargs = ['prog', 'init', '--ini', TEMP_KINTO_INI, '--backend', 'memory']
        with mock.patch.object(sys, 'argv', testargs):
            main()

        with open(TEMP_KINTO_INI) as f:
            content = f.read()
        assert 'memory' in content

    def test_cli_migrate_command_runs_init_schema(self):
        with mock.patch('kinto.__main__.scripts.migrate') as mocked_migrate:
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['migrate', '--ini', TEMP_KINTO_INI])
            assert res == 0
            assert mocked_migrate.call_count == 1

    def test_cli_delete_collection_run_delete_collection_script(self):
        with mock.patch('kinto.__main__.scripts.delete_collection') as del_col:
            del_col.return_value = mock.sentinel.del_col_code
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['delete-collection', '--ini', TEMP_KINTO_INI,
                        '--bucket', 'test_bucket',
                        '--collection', 'test_collection'])
            assert res == mock.sentinel.del_col_code
            assert del_col.call_count == 1

    def test_cli_rebuild_quotas_run_rebuild_quotas_script(self):
        with mock.patch('kinto.__main__.scripts.rebuild_quotas') as reb_quo:
            reb_quo.return_value = mock.sentinel.reb_quo_code
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['rebuild-quotas', '--ini', TEMP_KINTO_INI])
            assert res == mock.sentinel.reb_quo_code
            assert reb_quo.call_count == 1

    def test_cli_start_runs_pserve(self):
        with mock.patch('kinto.__main__.pserve.main') as mocked_pserve:
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['start', '--ini', TEMP_KINTO_INI])
            assert res == 0
            assert mocked_pserve.call_count == 1

    def test_cli_start_with_quiet_option_runs_pserve_with_quiet(self):
        with mock.patch('kinto.__main__.pserve.main') as mocked_pserve:
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['start', '-q', '--ini', TEMP_KINTO_INI])
            assert res == 0
            assert mocked_pserve.call_count == 1
            assert mocked_pserve.call_args[1]['argv'][1] == '-q'

    def test_cli_start_with_verbose_option_runs_pserve_with_verbose(self):
        with mock.patch('kinto.__main__.pserve.main') as mocked_pserve:
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['start', '-v', '--ini', TEMP_KINTO_INI])
            assert res == 0
            assert mocked_pserve.call_count == 1
            assert mocked_pserve.call_args[1]['argv'][1] == '-v'

    def test_cli_start_with_reload_runs_pserve_with_reload(self):
        with mock.patch('kinto.__main__.pserve.main') as mocked_pserve:
            res = main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            assert res == 0
            res = main(['start', '--reload', '--ini', TEMP_KINTO_INI])
            assert res == 0
            assert mocked_pserve.call_count == 1
            assert '--reload' in mocked_pserve.call_args[1]['argv']

    def test_cli_can_display_kinto_version(self):
        with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            res = main(['version'])
            assert mock_stdout.getvalue() == '{}\n'.format(kinto_version)
            assert res == 0

    def test_cli_can_configure_logger_in_quiet(self):
        with mock.patch('kinto.__main__.logging') as mocked_logging:
            main(['init', '-q', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            mocked_logging.basicConfig.assert_called_with(
                level=mocked_logging.CRITICAL,
                format=DEFAULT_LOG_FORMAT)

    def test_cli_can_configure_logger_in_debug(self):
        with mock.patch('kinto.__main__.logging') as mocked_logging:
            main(['init', '--debug', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            mocked_logging.basicConfig.assert_called_with(
                level=mocked_logging.DEBUG,
                format=DEFAULT_LOG_FORMAT)

    def test_cli_use_default_logging_logger(self):
        with mock.patch('kinto.__main__.logging') as mocked_logging:
            main(['init', '--ini', TEMP_KINTO_INI, '--backend', 'memory'])
            mocked_logging.basicConfig.assert_called_with(
                level=logging.INFO,
                format=DEFAULT_LOG_FORMAT)
