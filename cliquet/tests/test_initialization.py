import mock

from pyramid.config import Configurator

import cliquet
from .support import unittest


class InitializationTest(unittest.TestCase):
    def test_fails_if_no_version_is_specified(self):
        config = Configurator()
        self.assertRaises(ValueError, cliquet.initialize_cliquet, config)

    def test_fails_if_specified_version_is_not_string(self):
        config = Configurator()
        self.assertRaises(ValueError, cliquet.initialize_cliquet, config, 1.0)

    def test_uses_the_version_for_prefix(self):
        config = Configurator()
        cliquet.initialize_cliquet(config, '0.0.1', 'name')
        self.assertEqual(config.route_prefix, 'v0')

    def test_set_the_project_version_if_specified(self):
        config = Configurator()
        cliquet.initialize_cliquet(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['cliquet.project_version'],
                         '0.0.1')

    def test_set_the_project_version_from_settings_even_if_specified(self):
        config = Configurator(settings={'cliquet.project_version': '1.0'})
        cliquet.initialize_cliquet(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['cliquet.project_version'],
                         '1.0')

    def test_warns_if_project_name_is_empty(self):
        config = Configurator(settings={'cliquet.project_name': ''})
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.initialize_cliquet(config, '0.0.1')
            mocked.assert_called()

    def test_warns_if_project_name_is_missing(self):
        config = Configurator()
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.initialize_cliquet(config, '0.0.1')
            error_msg = 'No value specified for `project_name`'
            mocked.assert_called_with(error_msg)

    def test_set_the_project_name_if_specified(self):
        config = Configurator()
        cliquet.initialize_cliquet(config, '0.0.1', 'kinto')
        self.assertEqual(config.registry.settings['cliquet.project_name'],
                         'kinto')

    def test_set_the_project_name_from_settings_even_if_specified(self):
        config = Configurator(settings={'cliquet.project_name': 'kinto'})
        cliquet.initialize_cliquet(config, '0.0.1', 'readinglist')
        self.assertEqual(config.registry.settings['cliquet.project_name'],
                         'kinto')
