# -*- coding: utf-8 -*-
import mock
import webtest

from pyramid.config import Configurator
from pyramid.events import NewRequest
from pyramid.exceptions import ConfigurationError

import cliquet
from cliquet import initialization
from .support import unittest


class InitializationTest(unittest.TestCase):
    def test_fails_if_no_version_is_specified(self):
        config = Configurator()
        self.assertRaises(ConfigurationError, cliquet.initialize, config)

    def test_uses_the_version_for_prefix(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.route_prefix, 'v0')

    def test_set_the_project_version_if_specified(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['project_version'], '0.0.1')

    def test_project_version_uses_setting_if_specified(self):
        config = Configurator(settings={'cliquet.project_version': '1.0.0'})
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['project_version'], '1.0.0')

    def test_http_api_version_relies_on_project_version_by_default(self):
        config = Configurator()
        cliquet.initialize(config, '0.1.0', 'name')
        self.assertEqual(config.registry.settings['http_api_version'], '0.1')

    def test_http_api_version_uses_setting_if_specified(self):
        config = Configurator(settings={'cliquet.http_api_version': '1.3'})
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['http_api_version'], '1.3')

    def test_warns_if_project_name_is_empty(self):
        config = Configurator(settings={'cliquet.project_name': ''})
        with mock.patch('cliquet.initialization.warnings.warn') as mocked:
            cliquet.initialize(config, '0.0.1')
            error_msg = 'No value specified for `project_name`'
            mocked.assert_called_with(error_msg)

    def test_warns_if_project_name_is_missing(self):
        config = Configurator()
        with mock.patch('cliquet.initialization.warnings.warn') as mocked:
            cliquet.initialize(config, '0.0.1')
            error_msg = 'No value specified for `project_name`'
            mocked.assert_called_with(error_msg)

    def test_set_the_project_name_if_specified(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'kinto')
        self.assertEqual(config.registry.settings['project_name'],
                         'kinto')

    def test_set_the_project_name_from_settings_even_if_specified(self):
        config = Configurator(settings={'cliquet.project_name': 'kinto'})
        cliquet.initialize(config, '0.0.1', 'readinglist')
        self.assertEqual(config.registry.settings['project_name'],
                         'kinto')

    def test_default_settings_are_overriden_if_specified_in_initialize(self):
        config = Configurator()
        defaults = {'cliquet.paginate_by': 102}
        cliquet.initialize(config, '0.0.1', 'project_name',
                           default_settings=defaults)
        self.assertEqual(config.registry.settings['paginate_by'], 102)

    def test_default_settings_are_overriden_by_application(self):
        config = Configurator(settings={'cliquet.paginate_by': 10})
        cliquet.initialize(config, '0.0.1', 'project_name')
        self.assertEqual(config.registry.settings['paginate_by'], 10)

    def test_specified_default_settings_are_overriden_by_application(self):
        config = Configurator(settings={'cliquet.paginate_by': 5})
        defaults = {'cliquet.paginate_by': 10}
        cliquet.initialize(config, '0.0.1', 'project_name',
                           default_settings=defaults)
        self.assertEqual(config.registry.settings['paginate_by'], 5)

    def test_backends_are_not_instantiated_by_default(self):
        config = Configurator(settings=cliquet.DEFAULT_SETTINGS)
        cliquet.initialize(config, '0.0.1', 'project_name')
        self.assertFalse(hasattr(config.registry, 'storage'))
        self.assertFalse(hasattr(config.registry, 'cache'))
        self.assertFalse(hasattr(config.registry, 'permission'))

    def test_backends_type_is_checked_when_instantiated(self):
        def config_fails(settings):
            config = Configurator(settings=settings)
            with self.assertRaises(ConfigurationError):
                cliquet.initialize(config, '0.0.1', 'project_name')

        config_fails({'cliquet.storage_backend': 'cliquet.cache.memory'})
        config_fails({'cliquet.cache_backend': 'cliquet.storage.memory'})
        config_fails({'cliquet.permission_backend': 'cliquet.storage.memory'})

    def test_environment_values_override_configuration(self):
        import os

        envkey = 'CLIQUET_PROJECT_NAME'
        os.environ[envkey] = 'abc'

        config = Configurator(settings={'cliquet.project_name': 'kinto'})
        cliquet.initialize(config, '0.0.1')

        os.environ.pop(envkey)

        project_used = config.registry.settings['project_name']
        self.assertEqual(project_used, 'abc')

    def test_initialize_cliquet_is_deprecated(self):
        config = Configurator()
        with mock.patch('cliquet.initialization.warnings.warn') as mocked:
            cliquet.initialize_cliquet(config, '0.0.1', 'name')
            msg = ('cliquet.initialize_cliquet is now deprecated. '
                   'Please use "cliquet.initialize" instead')
            mocked.assert_called_with(msg, DeprecationWarning)


class ProjectSettingsTest(unittest.TestCase):
    def settings(self, provided):
        config = Configurator(settings=provided)
        cliquet.initialize(config, '1.0', 'kinto')
        return config.get_settings()

    def test_uses_unprefixed_name(self):
        settings = {
            'paginate_by': 3.14
        }
        self.assertEqual(self.settings(settings)['paginate_by'], 3.14)

    def test_uses_cliquet_prefix(self):
        settings = {
            'cliquet.paginate_by': 3.14
        }
        self.assertEqual(self.settings(settings)['paginate_by'], 3.14)

    def test_uses_project_name(self):
        settings = {
            'kinto.paginate_by': 42,
        }
        self.assertEqual(self.settings(settings)['paginate_by'], 42)

    def test_does_raise_valueerror_if_multiple_entries_are_equal(self):
        settings = {
            'paginate_by': 42,
            'cliquet.paginate_by': 42,
        }
        self.settings(settings)  # Not raising.

    def test_does_raise_valueerror_if_entries_are_not_hashable(self):
        settings = {
            'events.listeners': ['Rémy', 42],
        }
        self.settings(settings)  # Not raising.

    def test_raises_valueerror_if_different_multiple_entries(self):
        settings = {
            'paginate_by': 42,
            'cliquet.paginate_by': 3.14,
        }
        with self.assertRaises(ValueError):
            self.settings(settings)

        settings = {
            'kinto.paginate_by': 42,
            'cliquet.paginate_by': 3.14,
        }
        with self.assertRaises(ValueError):
            self.settings(settings)

    def test_environment_can_specify_project_name(self):
        import os

        envkey = 'KINTO_STORAGE_BACKEND'
        os.environ[envkey] = 'cliquet.storage.redis'
        settings = {
            'kinto.storage_backend': 'cliquet.storage.memory',
        }
        value = self.settings(settings)['storage_backend']
        os.environ.pop(envkey)
        self.assertEqual(value, 'cliquet.storage.redis')


class ApplicationWrapperTest(unittest.TestCase):

    @unittest.skipIf(initialization.newrelic is None,
                     "newrelic is not installed.")
    @mock.patch('cliquet.initialization.newrelic.agent')
    def test_newrelic_is_included_if_defined(self, mocked_newrelic):
        settings = {
            'newrelic_config': '/foo/bar.ini',
            'newrelic_env': 'test'
        }
        mocked_newrelic.WSGIApplicationWrapper.return_value = 'wrappedApp'
        app = cliquet.install_middlewares(mock.sentinel.app, settings)
        mocked_newrelic.initialize.assert_called_with('/foo/bar.ini', 'test')
        self.assertEquals(app, 'wrappedApp')

    @unittest.skipIf(initialization.newrelic is None,
                     "newrelic is not installed.")
    @mock.patch('cliquet.initialization.newrelic.agent')
    def test_newrelic_is_not_included_if_set_to_false(self, mocked_newrelic):
        settings = {'newrelic_config': False}
        app = cliquet.install_middlewares(mock.sentinel.app, settings)
        mocked_newrelic.initialize.assert_not_called()
        self.assertEquals(app, mock.sentinel.app)

    @mock.patch('cliquet.initialization.ProfilerMiddleware')
    def test_profiler_is_not_installed_if_set_to_false(self, mocked_profiler):
        settings = {'profiler_enabled': False}
        app = cliquet.install_middlewares(mock.sentinel.app, settings)
        mocked_profiler.initialize.assert_not_called()
        self.assertEquals(app, mock.sentinel.app)

    @mock.patch('cliquet.initialization.ProfilerMiddleware')
    def test_profiler_is_installed_if_set_to_true(self, mocked_profiler):
        settings = {
            'profiler_enabled': True,
            'profiler_dir': '/tmp/path'
        }
        mocked_profiler.return_value = 'wrappedApp'
        app = cliquet.install_middlewares(mock.sentinel.app, settings)

        mocked_profiler.assert_called_with(
            mock.sentinel.app,
            restrictions='*cliquet*',
            profile_dir='/tmp/path')

        self.assertEquals(app, 'wrappedApp')

    def test_load_default_settings_handle_prefix_attributes(self):
        config = mock.MagicMock()

        settings = {'project_name': 'myapp'}

        config.get_settings.return_value = settings
        initialization.load_default_settings(
            config, {'multiauth.policies': 'basicauth',
                     'cliquet.http_scheme': 'https',
                     'myapp.http_host': 'localhost:8888'})

        self.assertIn('multiauth.policies', settings)
        self.assertNotIn('policies', settings)
        self.assertEqual(settings['multiauth.policies'], 'basicauth')

        self.assertIn('http_scheme', settings)
        self.assertNotIn('cliquet.http_scheme', settings)
        self.assertEqual(settings['http_scheme'], 'https')

        self.assertIn('http_host', settings)
        self.assertNotIn('myapp.http_host', settings)
        self.assertEqual(settings['http_host'], 'localhost:8888')


class StatsDConfigurationTest(unittest.TestCase):
    def setUp(self):
        settings = cliquet.DEFAULT_SETTINGS.copy()
        settings['statsd_url'] = 'udp://host:8080'
        self.config = Configurator(settings=settings)
        self.config.registry.storage = {}
        self.config.registry.cache = {}
        self.config.registry.permission = {}

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_isnt_called_if_statsd_url_is_not_set(self, mocked):
        self.config.add_settings({
            'statsd_url': None
        })
        initialization.setup_statsd(self.config)
        mocked.assert_not_called()

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_to_none_if_statsd_url_not_set(self, mocked):
        self.config.add_settings({
            'statsd_url': None
        })
        initialization.setup_statsd(self.config)
        self.assertEqual(self.config.registry.statsd, None)

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_called_if_statsd_url_is_set(self, mocked):
        initialization.setup_statsd(self.config)
        mocked.assert_called_with('host', 8080, 'cliquet')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_expose_in_the_registry_if_url_is_set(self, mocked):
        initialization.setup_statsd(self.config)
        self.assertEqual(self.config.registry.statsd, mocked.return_value)

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_cache(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call({}, prefix='cache')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_storage(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call({}, prefix='storage')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_permission(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call({}, prefix='permission')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_authentication(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call(None, prefix='authentication')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_nothing_on_anonymous_requests(self, mocked):
        cliquet.initialize(self.config, '0.0.1', 'project_name')
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get('/')
        self.assertFalse(mocked.count.called)

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_views_and_methods(self, mocked):
        cliquet.initialize(self.config, '0.0.1', 'project_name')
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get('/v0/__heartbeat__')
        mocked().count.assert_any_call('view.heartbeat.GET')

    @mock.patch('cliquet.utils.hmac_digest')
    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_unique_users(self, mocked, digest_mocked):
        digest_mocked.return_value = u'mat'
        cliquet.initialize(self.config, '0.0.1', 'project_name')
        app = webtest.TestApp(self.config.make_wsgi_app())
        headers = {'Authorization': 'Basic bWF0Og=='}
        app.get('/v0/', headers=headers)
        mocked().count.assert_any_call('users', unique='basicauth:mat')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_authentication_types(self, mocked):
        cliquet.initialize(self.config, '0.0.1', 'project_name')
        app = webtest.TestApp(self.config.make_wsgi_app())
        headers = {'Authorization': 'Basic bWF0Og=='}
        app.get('/v0/', headers=headers)
        mocked().count.assert_any_call('authn_type.basicauth')


class RequestsConfigurationTest(unittest.TestCase):
    def _get_app(self, settings={}):
        app_settings = {
            'storage_backend': 'cliquet.storage.memory',
            'cache_backend': 'cliquet.cache.redis',
        }
        app_settings.update(**settings)
        config = Configurator(settings=app_settings)
        cliquet.initialize(config, '0.0.1', 'name')
        return webtest.TestApp(config.make_wsgi_app())

    def test_requests_have_a_bound_data_attribute(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'name')

        def on_new_request(event):
            data = event.request.bound_data
            self.assertEqual(data, {})
            self.assertEqual(id(data), id(event.request.bound_data))

        config.add_subscriber(on_new_request, NewRequest)
        app = webtest.TestApp(config.make_wsgi_app())
        app.get('/v0/')

    def test_subrequests_share_parent_bound_data(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'name')

        bound_datas = set()

        def on_new_request(event):
            bound_datas.add(id(event.request.bound_data))

        config.add_subscriber(on_new_request, NewRequest)
        app = webtest.TestApp(config.make_wsgi_app())
        app.post_json('/v0/batch', {'requests': [{'path': '/'}]})
        self.assertEqual(len(bound_datas), 1)

    def test_by_default_relies_on_pyramid_application_url(self):
        app = self._get_app()
        resp = app.get('/v0/')
        self.assertEqual(resp.json['url'], 'http://localhost/v0/')

    def test_by_default_relies_on_incoming_headers(self):
        app = self._get_app()
        resp = app.get('/v0/', headers={'Host': 'server:8888'})
        self.assertEqual(resp.json['url'], 'http://server:8888/v0/')

    def test_by_default_relies_on_wsgi_environment(self):
        app = self._get_app()
        environ = {
            'wsgi.url_scheme': 'https',
            'HTTP_HOST': 'server:44311'
        }
        resp = app.get('/v0/', extra_environ=environ)
        self.assertEqual(resp.json['url'], 'https://server:44311/v0/')

    def test_http_scheme_overrides_the_wsgi_environment(self):
        app = self._get_app({'http_scheme': 'http2'})
        environ = {
            'wsgi.url_scheme': 'https'
        }
        resp = app.get('/v0/', extra_environ=environ)
        self.assertEqual(resp.json['url'], 'http2://localhost:80/v0/')

    def test_http_host_overrides_the_wsgi_environment(self):
        app = self._get_app({'http_host': 'server'})
        environ = {
            'HTTP_HOST': 'elb:44311'
        }
        resp = app.get('/v0/', extra_environ=environ)
        self.assertEqual(resp.json['url'], 'http://server/v0/')

    def test_http_host_overrides_the_request_headers(self):
        app = self._get_app({'http_host': 'server'})
        resp = app.get('/v0/', headers={'Host': 'elb:8888'})
        self.assertEqual(resp.json['url'], 'http://server/v0/')


class PluginsTest(unittest.TestCase):
    def test_cliquet_includes_are_included_manually(self):
        config = Configurator(settings=cliquet.DEFAULT_SETTINGS)
        config.add_settings({'includes': 'elastic history'})
        config.route_prefix = 'v2'

        with mock.patch.object(config, 'include'):
            with mock.patch.object(config, 'scan'):
                cliquet.includeme(config)

                config.include.assert_any_call('elastic')
                config.include.assert_any_call('history')

    def make_app(self):
        config = Configurator(settings=cliquet.DEFAULT_SETTINGS)
        config.add_settings({
            'permission_backend': 'cliquet.permission.memory',
            'includes': 'cliquet.tests.testplugin'
        })
        cliquet.initialize(config, '0.0.1', 'name')
        return webtest.TestApp(config.make_wsgi_app())

    def test_plugin_can_define_protected_views(self):
        app = self.make_app()
        app.post('/v0/attachment', status=401)
        headers = {'Authorization': 'Basic bWF0OjE='}
        app.post('/v0/attachment', headers=headers, status=403)

    def test_plugin_benefits_from_cors_setup(self):
        app = self.make_app()
        headers = {
            'Origin': 'lolnet.org',
            'Access-Control-Request-Method': 'POST'
        }
        resp = app.options('/v0/attachment', headers=headers, status=200)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
