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
        config = Configurator(settings={'cliquet.project_version': '1.0.0'})
        cliquet.initialize_cliquet(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['cliquet.project_version'],
                         '1.0.0')

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

    def test_environment_values_override_configuration(self):
        import os

        envkey = 'CLIQUET_PROJECT_NAME'
        os.environ[envkey] = 'abc'

        config = Configurator(settings={'cliquet.project_name': 'kinto'})
        cliquet.initialize_cliquet(config, '0.0.1')

        os.environ.pop(envkey)

        project_used = config.registry.settings['cliquet.project_name']
        self.assertEqual(project_used, 'abc')


class SentryConfigurationTest(unittest.TestCase):

    @mock.patch('cliquet.raven.Client')
    def test_sentry_isnt_called_if_sentry_url_is_not_set(self, mocked_raven):
        config = Configurator(settings={
            'cliquet.sentry_url': None
        })
        cliquet.handle_sentry(config)
        mocked_raven.assert_not_called()

    @mock.patch('cliquet.raven.Client')
    def test_sentry_is_called_if_sentry_url_is_set(self, mocked_raven):
        config = Configurator(settings={
            'cliquet.sentry_url': 'http://public:secret@example.org/1',
            'cliquet.sentry_projects': 'foo,bar',
            'cliquet.project_name': 'name',
            'cliquet.project_version': 'x.y.z'
        })
        cliquet.handle_sentry(config)
        mocked_raven.assert_called_with(
            'http://public:secret@example.org/1',
            release='x.y.z',
            include_paths=['cornice', 'cliquet', 'foo,bar']
        )

    @mock.patch('cliquet.raven.Client')
    def test_sentry_sends_message_on_startup(self, mocked_raven):
        mocked_client = mock.MagicMock()
        mocked_raven.return_value = mocked_client
        config = Configurator(settings={
            'cliquet.sentry_url': 'http://public:secret@example.org/1',
            'cliquet.sentry_projects': 'foo,bar',
            'cliquet.project_name': 'name',
            'cliquet.project_version': 'x.y.z'
        })
        cliquet.handle_sentry(config)
        mocked_client.captureMessage.assert_called_once_with(
            'name x.y.z starting.')
