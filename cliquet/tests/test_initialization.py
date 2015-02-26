import mock

import cliquet
from .support import unittest


class InitializationTest(unittest.TestCase):
    def _get_config(self, settings):
        get_settings = mock.Mock(return_value=settings)
        config = mock.MagicMock(get_settings=get_settings)
        return config

    def _assertInitWarns(self, settings, error_msg):
        config = self._get_config(settings)
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.includeme(config)
            mocked.assert_called_with(error_msg)

    def test_warns_if_project_name_is_empty(self):
        settings = {'cliquet.project_docs': 'online'}
        error_msg = 'No value for `project_name` in settings'
        self._assertInitWarns(settings, error_msg)

    def test_warns_if_project_docs_is_empty(self):
        settings = {'cliquet.project_name': 'myproject'}
        error_msg = 'No value for `project_docs` in settings'
        self._assertInitWarns(settings, error_msg)
