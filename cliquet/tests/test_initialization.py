import mock
import webtest

from pyramid.config import Configurator

import cliquet
from cliquet import initialization
from .support import unittest


class InitializationTest(unittest.TestCase):
    def test_fails_if_no_version_is_specified(self):
        config = Configurator()
        self.assertRaises(ValueError, cliquet.initialize, config)

    def test_fails_if_specified_version_is_not_string(self):
        config = Configurator()
        self.assertRaises(ValueError, cliquet.initialize, config, 1.0)

    def test_uses_the_version_for_prefix(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.route_prefix, 'v0')

    def test_set_the_project_version_if_specified(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['cliquet.project_version'],
                         '0.0.1')

    def test_set_the_project_version_from_settings_even_if_specified(self):
        config = Configurator(settings={'cliquet.project_version': '1.0.0'})
        cliquet.initialize(config, '0.0.1', 'name')
        self.assertEqual(config.registry.settings['cliquet.project_version'],
                         '1.0.0')

    def test_warns_if_project_name_is_empty(self):
        config = Configurator(settings={'cliquet.project_name': ''})
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.initialize(config, '0.0.1')
            error_msg = 'No value specified for `project_name`'
            mocked.assert_called_with(error_msg)

    def test_warns_if_project_name_is_missing(self):
        config = Configurator()
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.initialize(config, '0.0.1')
            error_msg = 'No value specified for `project_name`'
            mocked.assert_called_with(error_msg)

    def test_set_the_project_name_if_specified(self):
        config = Configurator()
        cliquet.initialize(config, '0.0.1', 'kinto')
        self.assertEqual(config.registry.settings['cliquet.project_name'],
                         'kinto')

    def test_set_the_project_name_from_settings_even_if_specified(self):
        config = Configurator(settings={'cliquet.project_name': 'kinto'})
        cliquet.initialize(config, '0.0.1', 'readinglist')
        self.assertEqual(config.registry.settings['cliquet.project_name'],
                         'kinto')

    def test_overriden_default_settings(self):
        config = Configurator()
        defaults = {'cliquet.paginate_by': 102}
        cliquet.initialize(config, '0.0.1', default_settings=defaults)
        self.assertEqual(config.registry.settings['cliquet.paginate_by'], 102)

    def test_environment_values_override_configuration(self):
        import os

        envkey = 'CLIQUET_PROJECT_NAME'
        os.environ[envkey] = 'abc'

        config = Configurator(settings={'cliquet.project_name': 'kinto'})
        cliquet.initialize(config, '0.0.1')

        os.environ.pop(envkey)

        project_used = config.registry.settings['cliquet.project_name']
        self.assertEqual(project_used, 'abc')

    def test_warn_if_deprecated_settings_are_used(self):
        config = Configurator(settings={'cliquet.cache_pool_maxconn': '1'})
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.initialize(config, '0.0.1')
            msg = ("'cliquet.cache_pool_maxconn' setting is deprecated. "
                   "Use 'cliquet.cache_pool_size' instead.")
            mocked.assert_called_with(msg, DeprecationWarning)

    def test_initialize_cliquet_is_deprecated(self):
        config = Configurator()
        with mock.patch('cliquet.warnings.warn') as mocked:
            cliquet.initialize_cliquet(config, '0.0.1', 'name')
            msg = ('cliquet.initialize_cliquet is now deprecated. '
                   'Please use "cliquet.initialize" instead')
            mocked.assert_called_with(msg, DeprecationWarning)


class ApplicationWrapperTest(unittest.TestCase):

    @mock.patch('cliquet.initialization.newrelic.agent')
    def test_newrelic_is_included_if_defined(self, mocked_newrelic):
        settings = {
            'cliquet.newrelic_config': '/foo/bar.ini',
            'cliquet.newrelic_env': 'test'
        }
        mocked_newrelic.WSGIApplicationWrapper.return_value = 'wrappedApp'
        app = cliquet.install_middlewares(mock.sentinel.app, settings)
        mocked_newrelic.initialize.assert_called_with('/foo/bar.ini', 'test')
        self.assertEquals(app, 'wrappedApp')

    @mock.patch('cliquet.initialization.newrelic.agent')
    def test_newrelic_is_not_included_if_set_to_false(self, mocked_newrelic):
        settings = {'cliquet.newrelic_config': False}
        app = cliquet.install_middlewares(mock.sentinel.app, settings)
        mocked_newrelic.initialize.assert_not_called()
        self.assertEquals(app, mock.sentinel.app)

    @mock.patch('cliquet.initialization.ProfilerMiddleware')
    def test_profiler_is_not_installed_if_set_to_false(self, mocked_profiler):
        settings = {'cliquet.profiler_enabled': False}
        app = cliquet.install_middlewares(mock.sentinel.app, settings)
        mocked_profiler.initialize.assert_not_called()
        self.assertEquals(app, mock.sentinel.app)

    @mock.patch('cliquet.initialization.ProfilerMiddleware')
    def test_profiler_is_installed_if_set_to_true(self, mocked_profiler):
        settings = {
            'cliquet.profiler_enabled': True,
            'cliquet.profiler_dir': '/tmp/path'
        }
        mocked_profiler.return_value = 'wrappedApp'
        app = cliquet.install_middlewares(mock.sentinel.app, settings)

        mocked_profiler.assert_called_with(
            mock.sentinel.app,
            restrictions='*cliquet*',
            profile_dir=('/tmp/path',))

        self.assertEquals(app, 'wrappedApp')


class StatsDConfigurationTest(unittest.TestCase):
    def setUp(self):
        settings = cliquet.DEFAULT_SETTINGS.copy()
        settings['cliquet.statsd_url'] = 'udp://host:8080'
        self.config = Configurator(settings=settings)
        self.config.registry.storage = {}
        self.config.registry.cache = {}

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_isnt_called_if_statsd_url_is_not_set(self, mocked):
        self.config.add_settings({
            'cliquet.statsd_url': None
        })
        initialization.setup_statsd(self.config)
        mocked.assert_not_called()

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_called_if_statsd_url_is_set(self, mocked):
        initialization.setup_statsd(self.config)
        mocked.assert_called_with('host', 8080, 'cliquet')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_cache(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call({}, prefix='cache')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_storage(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call({}, prefix='storage')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_is_set_on_authentication(self, mocked):
        c = initialization.setup_statsd(self.config)
        c.watch_execution_time.assert_any_call(None, prefix='authentication')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_nothing_on_anonymous_requests(self, mocked):
        cliquet.initialize(self.config, '0.0.1')
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get('/')
        self.assertFalse(mocked.count.called)

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_views_and_methods(self, mocked):
        cliquet.initialize(self.config, '0.0.1')
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get('/v0/__heartbeat__')
        mocked().count.assert_any_call('view.heartbeat.GET')

    @mock.patch('cliquet.utils.hmac_digest')
    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_unique_users(self, mocked, digest_mocked):
        digest_mocked.return_value = u'mat'
        cliquet.initialize(self.config, '0.0.1')
        app = webtest.TestApp(self.config.make_wsgi_app())
        headers = {'Authorization': 'Basic bWF0Og=='}
        app.get('/v0/__heartbeat__', headers=headers)
        mocked().count.assert_any_call('users', unique='basicauth_mat')

    @mock.patch('cliquet.statsd.Client')
    def test_statsd_counts_authentication_types(self, mocked):
        cliquet.initialize(self.config, '0.0.1')
        app = webtest.TestApp(self.config.make_wsgi_app())
        headers = {'Authorization': 'Basic bWF0Og=='}
        app.get('/v0/__heartbeat__', headers=headers)
        mocked().count.assert_any_call('authn_type.BasicAuth')


class RequestsConfigurationTest(unittest.TestCase):
    def _get_app(self, settings={}):
        app_settings = {
            'cliquet.storage_backend': 'cliquet.storage.memory',
            'cliquet.cache_backend': 'cliquet.cache.redis',
        }
        app_settings.update(**settings)
        config = Configurator(settings=app_settings)
        cliquet.initialize(config, '0.0.1', 'name')
        return webtest.TestApp(config.make_wsgi_app())

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
        app = self._get_app({'cliquet.http_scheme': 'http2'})
        environ = {
            'wsgi.url_scheme': 'https'
        }
        resp = app.get('/v0/', extra_environ=environ)
        self.assertEqual(resp.json['url'], 'http2://localhost:80/v0/')

    def test_http_host_overrides_the_wsgi_environment(self):
        app = self._get_app({'cliquet.http_host': 'server'})
        environ = {
            'HTTP_HOST': 'elb:44311'
        }
        resp = app.get('/v0/', extra_environ=environ)
        self.assertEqual(resp.json['url'], 'http://server/v0/')

    def test_http_host_overrides_the_request_headers(self):
        app = self._get_app({'cliquet.http_host': 'server'})
        resp = app.get('/v0/', headers={'Host': 'elb:8888'})
        self.assertEqual(resp.json['url'], 'http://server/v0/')
