import warnings
from unittest import mock

import webtest
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.config import Configurator
from pyramid.events import NewRequest
from pyramid.exceptions import ConfigurationError

import kinto.core
from kinto.core import initialization
from kinto.core.testing import get_user_headers, skip_if_no_statsd, unittest


class InitializationTest(unittest.TestCase):
    def test_fails_if_no_version_is_specified(self):
        config = Configurator()
        self.assertRaises(ConfigurationError, kinto.core.initialize, config)

    def test_uses_the_version_for_prefix(self):
        config = Configurator()
        kinto.core.initialize(config, "0.0.1", "name")
        self.assertEqual(config.route_prefix, "v0")

    def test_set_the_project_version_if_specified(self):
        config = Configurator()
        kinto.core.initialize(config, "0.0.1", "name")
        self.assertEqual(config.registry.settings["project_version"], "0.0.1")

    def test_project_version_uses_setting_if_specified(self):
        config = Configurator(settings={"name.project_version": "1.0.0"})
        kinto.core.initialize(config, "0.0.1", "name")
        self.assertEqual(config.registry.settings["project_version"], "1.0.0")

    def test_http_api_version_relies_on_project_version_by_default(self):
        config = Configurator()
        kinto.core.initialize(config, "0.1.0", "name")
        self.assertEqual(config.registry.settings["http_api_version"], "0.1")

    def test_http_api_version_uses_setting_if_specified(self):
        config = Configurator(settings={"name.http_api_version": "1.3"})
        kinto.core.initialize(config, "0.0.1", "name")
        self.assertEqual(config.registry.settings["http_api_version"], "1.3")

    def test_warns_if_settings_prefix_is_empty(self):
        config = Configurator(settings={"kinto.settings_prefix": ""})
        with mock.patch("kinto.core.initialization.warnings.warn") as mocked:
            kinto.core.initialize(config, "0.0.1")
            error_msg = "No value specified for `settings_prefix`"
            mocked.assert_any_call(error_msg)

    def test_warns_if_settings_prefix_is_missing(self):
        config = Configurator()
        with mock.patch("kinto.core.initialization.warnings.warn") as mocked:
            kinto.core.initialize(config, "0.0.1")
            error_msg = "No value specified for `settings_prefix`"
            mocked.assert_any_call(error_msg)

    def test_set_the_settings_prefix_if_specified(self):
        config = Configurator()
        kinto.core.initialize(config, "0.0.1", "kinto")
        self.assertEqual(config.registry.settings["settings_prefix"], "kinto")

    def test_set_the_settings_prefix_from_settings_even_if_specified(self):
        config = Configurator(settings={"kinto.settings_prefix": "kinto"})
        kinto.core.initialize(config, "0.0.1", "readinglist")
        self.assertEqual(config.registry.settings["settings_prefix"], "kinto")

    def test_warns_if_not_https(self):
        error_msg = "HTTPS is not enabled"
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter("always")

            config = Configurator(
                settings={"settings_prefix": "kinto", "kinto.http_scheme": "https"}
            )
            kinto.core.initialize(config, "0.0.1")
            self.assertFalse(any(error_msg in str(w.message) for w in warns))

            config = Configurator(settings={"kinto.http_scheme": "http"})
            kinto.core.initialize(config, "0.0.1")
            self.assertTrue(any(error_msg in str(w.message) for w in warns))

    def test_default_settings_are_overriden_if_specified_in_initialize(self):
        config = Configurator()
        defaults = {"paginate_by": 102}
        kinto.core.initialize(config, "0.0.1", "prefix", default_settings=defaults)
        self.assertEqual(config.registry.settings["paginate_by"], 102)

    def test_default_settings_are_overriden_by_application(self):
        config = Configurator(settings={"prefix.paginate_by": 10})
        kinto.core.initialize(config, "0.0.1", "prefix")
        self.assertEqual(config.registry.settings["paginate_by"], 10)

    def test_specified_default_settings_are_overriden_by_application(self):
        config = Configurator(settings={"settings_prefix.paginate_by": 5})
        defaults = {"settings_prefix.paginate_by": 10}
        kinto.core.initialize(config, "0.0.1", "settings_prefix", default_settings=defaults)
        self.assertEqual(config.registry.settings["paginate_by"], 5)

    def test_backends_are_not_instantiated_by_default(self):
        config = Configurator(settings={**kinto.core.DEFAULT_SETTINGS})
        kinto.core.initialize(config, "0.0.1", "settings_prefix")
        self.assertFalse(hasattr(config.registry, "storage"))
        self.assertFalse(hasattr(config.registry, "cache"))
        self.assertFalse(hasattr(config.registry, "permission"))

    def test_backends_type_is_checked_when_instantiated(self):
        def config_fails(settings):
            config = Configurator(settings=settings)
            with self.assertRaises(ConfigurationError):
                kinto.core.initialize(config, "0.0.1", "settings_prefix")

        config_fails({"settings_prefix.storage_backend": "kinto.core.cache.memory"})
        config_fails({"settings_prefix.cache_backend": "kinto.core.storage.memory"})
        config_fails({"settings_prefix.permission_backend": "kinto.core.storage.memory"})

    def test_environment_values_override_configuration(self):
        import os

        envkey = "KINTO_SETTINGS_PREFIX"
        os.environ[envkey] = "abc"

        config = Configurator(settings={"kinto.settings_prefix": "kinto"})
        kinto.core.initialize(config, "0.0.1")

        os.environ.pop(envkey)

        prefix_used = config.registry.settings["settings_prefix"]
        self.assertEqual(prefix_used, "abc")

    def test_statsd_plugin_isnt_included_by_default(self):
        config = Configurator()
        with mock.patch("kinto.plugins.statsd.StatsDService") as mocked:
            kinto.core.initialize(config, "0.0.1", "prefix")
        mocked.assert_not_called()


class ProjectSettingsTest(unittest.TestCase):
    def settings(self, provided):
        config = Configurator(settings=provided)
        kinto.core.initialize(config, "1.0", "myproject")
        return config.get_settings()

    def test_uses_unprefixed_name(self):
        settings = {"paginate_by": 3.14}
        self.assertEqual(self.settings(settings)["paginate_by"], 3.14)

    def test_uses_settings_prefix(self):
        settings = {"myproject.paginate_by": 42}
        self.assertEqual(self.settings(settings)["paginate_by"], 42)

    def test_does_raise_valueerror_if_multiple_entries_are_equal(self):
        settings = {"paginate_by": 42, "myproject.paginate_by": 42}
        self.settings(settings)  # Not raising.

    def test_does_raise_valueerror_if_entries_are_not_hashable(self):
        settings = {"events.listeners": ["Rémy", 42]}
        self.settings(settings)  # Not raising.

    def test_raises_valueerror_if_different_multiple_entries(self):
        settings = {"paginate_by": 42, "myproject.paginate_by": 3.14}
        with self.assertRaises(ValueError):
            self.settings(settings)

    def test_environment_can_specify_settings_prefix(self):
        import os

        envkey = "MYPROJECT_CACHE_BACKEND"  # MYPROJECT_ prefix
        os.environ[envkey] = "kinto.core.cache.memory"
        settings = {"kinto.cache_backend": "kinto.core.cache.memcached"}
        value = self.settings(settings)["cache_backend"]
        os.environ.pop(envkey)
        self.assertEqual(value, "kinto.core.cache.memory")


class ApplicationWrapperTest(unittest.TestCase):
    @unittest.skipIf(initialization.newrelic is None, "newrelic is not installed.")
    @mock.patch("kinto.core.initialization.newrelic.agent")
    def test_newrelic_is_included_if_defined(self, mocked_newrelic):
        settings = {"newrelic_config": "/foo/bar.ini", "newrelic_env": "test"}
        mocked_newrelic.WSGIApplicationWrapper.return_value = "wrappedApp"
        app = kinto.core.install_middlewares(mock.sentinel.app, settings)
        mocked_newrelic.initialize.assert_called_with("/foo/bar.ini", "test")
        self.assertEqual(app, "wrappedApp")

    @unittest.skipIf(initialization.newrelic is None, "newrelic is not installed.")
    @mock.patch("kinto.core.initialization.newrelic.agent")
    def test_newrelic_is_not_included_if_set_to_false(self, mocked_newrelic):
        settings = {"newrelic_config": False}
        app = kinto.core.install_middlewares(mock.sentinel.app, settings)
        mocked_newrelic.initialize.assert_not_called()
        self.assertEqual(app, mock.sentinel.app)

    @mock.patch("kinto.core.initialization.ProfilerMiddleware")
    def test_profiler_is_not_installed_if_set_to_false(self, mocked_profiler):
        settings = {"profiler_enabled": False}
        app = kinto.core.install_middlewares(mock.sentinel.app, settings)
        mocked_profiler.initialize.assert_not_called()
        self.assertEqual(app, mock.sentinel.app)

    @mock.patch("kinto.core.initialization.ProfilerMiddleware")
    def test_profiler_is_installed_if_set_to_true(self, mocked_profiler):
        settings = {"profiler_enabled": True, "profiler_dir": "/tmp/path"}
        mocked_profiler.return_value = "wrappedApp"
        app = kinto.core.install_middlewares(mock.sentinel.app, settings)

        mocked_profiler.assert_called_with(
            mock.sentinel.app, restrictions="*kinto.core*", profile_dir="/tmp/path"
        )

        self.assertEqual(app, "wrappedApp")

    def test_load_default_settings_handle_prefix_attributes(self):
        config = mock.MagicMock()

        settings = {"settings_prefix": "myapp"}

        config.get_settings.return_value = settings
        initialization.load_default_settings(
            config,
            {
                "multiauth.policies": "basicauth",
                "myapp.http_scheme": "https",
                "myapp.http_host": "localhost:8888",
            },
        )

        self.assertIn("multiauth.policies", settings)
        self.assertNotIn("policies", settings)
        self.assertEqual(settings["multiauth.policies"], "basicauth")

        self.assertIn("http_scheme", settings)
        self.assertNotIn("kinto.http_scheme", settings)
        self.assertEqual(settings["http_scheme"], "https")

        self.assertIn("http_host", settings)
        self.assertNotIn("myapp.http_host", settings)
        self.assertEqual(settings["http_host"], "localhost:8888")

    def test_load_default_settings_converts_to_native_correctly(self):
        config = mock.MagicMock()

        settings = {"settings_prefix": "myapp"}

        config.get_settings.return_value = settings
        initialization.load_default_settings(config, {"myapp.my_cool_setting": '"1.2"'})

        self.assertEqual(settings["my_cool_setting"], "1.2")


class SentryTest(unittest.TestCase):
    @unittest.skipIf(initialization.sentry_sdk is None, "sentry is not installed.")
    def test_sentry_not_enabled_by_default(self):
        config = Configurator()
        with mock.patch("sentry_sdk.init") as mocked:
            kinto.core.initialize(config, "0.0.1")

        self.assertFalse(mocked.called)

    @unittest.skipIf(initialization.sentry_sdk is None, "sentry is not installed.")
    def test_sentry_enabled_if_sentry_dsn_is_set(self):
        config = Configurator(
            settings={
                "sentry_dsn": "https://notempty",
                "sentry_env": "local",
            }
        )
        with mock.patch("sentry_sdk.init") as mocked:
            kinto.core.initialize(config, "0.0.1")

        init_call = mocked.call_args_list[0]
        self.assertEqual(init_call[0][0], "https://notempty")
        self.assertEqual(init_call[1]["environment"], "local")

    @unittest.skipIf(initialization.sentry_sdk is None, "sentry is not installed.")
    def test_message_is_sent_on_startup(self):
        config = Configurator(
            settings={
                **kinto.core.DEFAULT_SETTINGS,
                "storage_backend": "kinto.core.storage.memory",
                "cache_backend": "kinto.core.cache.memory",
                "permission_backend": "kinto.core.permission.memory",
            }
        )
        config.add_settings(
            {
                "sentry_dsn": "https://notempty",
            }
        )

        with mock.patch("sentry_sdk.init"):
            kinto.core.initialize(config, "0.0.1", "name")

            with mock.patch("sentry_sdk.capture_message") as mocked:
                config.make_wsgi_app()

        mocked.assert_called_with("Running  0.0.1.", "info")

    @unittest.skipIf(initialization.sentry_sdk is None, "sentry is not installed.")
    def unexpected_exceptions_are_reported(self):
        with mock.patch("kinto.core.views.hello.get_eos", side_effect=ValueError):
            with mock.patch("sentry_sdk.hub.Hub.capture_event") as mocked:
                resp = self.app.get("/")
        assert resp.status == 500
        assert len(mocked.call_args_list) > 0


@skip_if_no_statsd
class MetricsConfigurationTest(unittest.TestCase):
    settings = {
        **kinto.core.DEFAULT_SETTINGS,
        "includes": "kinto.plugins.statsd",
        "statsd_url": "udp://host:8080",
        "multiauth.policies": "basicauth",
    }

    def setUp(self):
        patch = mock.patch("kinto.plugins.statsd.StatsDService")
        self.mocked = patch.start()
        self.addCleanup(patch.stop)

        patch_watch = mock.patch("kinto.core.metrics.watch_execution_time")
        self.mocked_watch = patch_watch.start()
        self.addCleanup(patch_watch.stop)

        self.config = Configurator(settings=self.settings)
        self.config.registry.storage = {}
        self.config.registry.cache = {}
        self.config.registry.permission = {}

    #
    # Backends.
    #

    def test_statsd_is_set_on_cache(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        _app = webtest.TestApp(self.config.make_wsgi_app())

        self.mocked_watch.assert_any_call(self.mocked(), {}, prefix="backend")

    def test_statsd_is_set_on_storage(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        _app = webtest.TestApp(self.config.make_wsgi_app())

        self.mocked_watch.assert_any_call(self.mocked(), {}, prefix="backend")

    def test_statsd_is_set_on_permission(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        _app = webtest.TestApp(self.config.make_wsgi_app())

        self.mocked_watch.assert_any_call(self.mocked(), {}, prefix="backend")

    #
    # Authentication.
    #

    def test_statsd_is_set_on_authentication_multiauth(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        _app = webtest.TestApp(self.config.make_wsgi_app())

        self.mocked_watch.assert_any_call(
            self.mocked(), mock.ANY, prefix="authentication", classname="basicauth"
        )

    def test_statsd_is_set_on_authentication_raw_auth(self):
        authn_policy = SessionAuthenticationPolicy()
        self.config.set_authentication_policy(authn_policy)

        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        _app = webtest.TestApp(self.config.make_wsgi_app())

        self.mocked_watch.assert_any_call(self.mocked(), mock.ANY, prefix="authentication")

    @mock.patch("kinto.core.utils.hmac_digest")
    def test_statsd_counts_unique_users(self, digest_mocked):
        digest_mocked.return_value = "mat"
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/", headers=get_user_headers("bob"))
        self.mocked().count.assert_any_call(
            "users", unique=[("auth", "basicauth"), ("userid", "mat")]
        )

    def test_statsd_counts_authentication_types(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/", headers=get_user_headers("bob"))
        self.mocked().count.assert_any_call("authentication", unique=[("type", "basicauth")])

    #
    # Endpoints.
    #

    def test_statsd_counts_nothing_on_anonymous_requests(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/")
        self.assertFalse(self.mocked.count.called)

    def test_statsd_counts_endpoints(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/__heartbeat__")
        self.mocked().count.assert_any_call(
            "request_summary",
            unique=[("method", "get"), ("endpoint", "heartbeat"), ("status", "200")],
        )

    def test_statsd_sanitizes_url_in_metrics(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get(
            "/v0/changeset'%7C%22%3F%3E%3C!DOCTYPE%22http://xh3E'),'/l')%20from%20dual)%7C'",
            status=404,
        )
        self.mocked().count.assert_any_call(
            "request_summary",
            unique=[
                ("method", "get"),
                (
                    "endpoint",
                    "unknown",
                ),
                ("status", "404"),
            ],
        )

    def test_statsd_observe_request_size(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/__heartbeat__")
        self.mocked().observe.assert_any_call(
            "request_size",
            len("{}"),
            labels=[("method", "get"), ("endpoint", "heartbeat")],
        )

    def test_statsd_observe_request_duration(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/__heartbeat__")
        self.mocked().timer.assert_any_call(
            "request_duration_seconds",
            value=mock.ANY,
            labels=[("method", "get"), ("endpoint", "heartbeat")],
        )

    def test_statsd_counts_unknown_urls(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/coucou", status=404)
        self.assertFalse(self.mocked.count.called)

    def test_statsd_is_noop_service_if_statsd_url_not_set(self):
        self.config.add_settings({"statsd_url": None})

        initialization.setup_metrics(self.config)

        self.assertEqual(self.config.registry.statsd.__class__.__name__, "NoOpMetricsService")

    def test_metrics_attr_is_set_if_statsd_url_is_set(self):
        self.config.add_settings({"statsd_url": "udp://host:8080"})

        initialization.setup_metrics(self.config)

        self.assertIsNotNone(self.config.registry.statsd)
        self.assertIsNotNone(self.config.registry.metrics)

    def test_statsd_attr_is_exposed_in_the_registry_if_url_is_set(self):
        self.config.add_settings({"statsd_url": "udp://host:8080"})

        initialization.setup_metrics(self.config)

        with mock.patch("warnings.warn") as mocked_warnings:
            self.config.registry.statsd.count("key")
            mocked_warnings.assert_called_with(
                "``config.registry.statsd`` is now deprecated. Use ``config.registry.metrics`` instead.",
                DeprecationWarning,
            )


class RequestsConfigurationTest(unittest.TestCase):
    app_settings = {
        "storage_backend": "kinto.core.storage.memory",
        "cache_backend": "kinto.core.cache.memory",
        "permission_backend": "kinto.core.permission.memory",
    }

    def _get_app(self, settings={}):
        config = Configurator(settings={**self.app_settings, **settings})
        kinto.core.initialize(config, "0.0.1", "name")
        return webtest.TestApp(config.make_wsgi_app())

    def test_requests_have_a_bound_data_attribute(self):
        config = Configurator(settings={**self.app_settings})
        kinto.core.initialize(config, "0.0.1", "name")

        def on_new_request(event):
            data = event.request.bound_data
            self.assertEqual(data, {})
            self.assertEqual(id(data), id(event.request.bound_data))

        config.add_subscriber(on_new_request, NewRequest)
        app = webtest.TestApp(config.make_wsgi_app())
        app.get("/v0/")

    def test_subrequests_share_parent_bound_data(self):
        config = Configurator(settings={**self.app_settings})
        kinto.core.initialize(config, "0.0.1", "name")

        bound_datas = set()

        def on_new_request(event):
            bound_datas.add(id(event.request.bound_data))

        config.add_subscriber(on_new_request, NewRequest)
        app = webtest.TestApp(config.make_wsgi_app())
        app.post_json("/v0/batch", {"requests": [{"path": "/"}]})
        self.assertEqual(len(bound_datas), 1)

    def test_by_default_relies_on_pyramid_application_url(self):
        app = self._get_app()
        resp = app.get("/v0/")
        self.assertEqual(resp.json["url"], "http://localhost/v0/")

    def test_by_default_relies_on_incoming_headers(self):
        app = self._get_app()
        resp = app.get("/v0/", headers={"Host": "server:8888"})
        self.assertEqual(resp.json["url"], "http://server:8888/v0/")

    def test_by_default_relies_on_wsgi_environment(self):
        app = self._get_app()
        environ = {"wsgi.url_scheme": "https", "HTTP_HOST": "server:44311"}
        resp = app.get("/v0/", extra_environ=environ)
        self.assertEqual(resp.json["url"], "https://server:44311/v0/")

    def test_http_scheme_overrides_the_wsgi_environment(self):
        app = self._get_app({"http_scheme": "http2"})
        environ = {"wsgi.url_scheme": "https"}
        resp = app.get("/v0/", extra_environ=environ)
        self.assertEqual(resp.json["url"], "http2://localhost:80/v0/")

    def test_http_host_overrides_the_wsgi_environment(self):
        app = self._get_app({"http_host": "server"})
        environ = {"HTTP_HOST": "elb:44311"}
        resp = app.get("/v0/", extra_environ=environ)
        self.assertEqual(resp.json["url"], "http://server/v0/")

    def test_http_host_overrides_the_request_headers(self):
        app = self._get_app({"http_host": "server"})
        resp = app.get("/v0/", headers={"Host": "elb:8888"})
        self.assertEqual(resp.json["url"], "http://server/v0/")


class PluginsTest(unittest.TestCase):
    def test_kinto_core_includes_are_included_manually(self):
        config = Configurator(settings={**kinto.core.DEFAULT_SETTINGS})
        config.add_settings({"includes": "elastic history"})
        config.route_prefix = "v2"

        with mock.patch.object(config, "include"):
            with mock.patch.object(config, "scan"):
                kinto.core.includeme(config)

                config.include.assert_any_call("elastic")
                config.include.assert_any_call("history")

    def make_app(self, settings=None):
        config = Configurator(settings={**kinto.core.DEFAULT_SETTINGS})
        config.add_settings(
            {
                "storage_backend": "kinto.core.storage.memory",
                "cache_backend": "kinto.core.cache.memory",
                "permission_backend": "kinto.core.permission.memory",
                "includes": "tests.core.testplugin",
                "multiauth.policies": "basicauth",
            },
            **(settings or {}),
        )
        kinto.core.initialize(config, "0.0.1", "name")
        return webtest.TestApp(config.make_wsgi_app())

    def test_plugin_can_define_protected_views(self):
        app = self.make_app()
        app.post("/v0/attachment", status=401)
        headers = {"Authorization": "Basic bWF0OjE="}
        app.post("/v0/attachment", headers=headers, status=403)

    def test_plugin_benefits_from_cors_setup(self):
        app = self.make_app()
        headers = {"Origin": "lolnet.org", "Access-Control-Request-Method": "POST"}
        resp = app.options("/v0/attachment", headers=headers, status=200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)

    def test_write_http_methods_are_rejected_if_readonly(self):
        app = self.make_app({"readonly": True})
        # `pytest.mark.parametrize` is not available on `TestCase` methods.
        for method, status in [
            ("GET", 200),
            ("HEAD", 200),
            ("OPTIONS", 200),
            ("POST", 405),
            ("PUT", 405),
            ("PATCH", 405),
            ("DELETE", 405),
        ]:
            app.request(
                "/v0/log",
                method=method,
                status=status,
                headers={
                    "Access-Control-Request-Method": method,
                    "Origin": "http://server.com",
                },
            )
