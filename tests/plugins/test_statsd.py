from unittest import mock

import webtest
from pyramid import testing
from pyramid.config import Configurator
from pyramid.exceptions import ConfigurationError

import kinto
from kinto.core.testing import skip_if_no_statsd, unittest
from kinto.plugins import statsd

from ..support import BaseWebTest


class StatsDIncludeTest(unittest.TestCase):
    def setUp(self):
        settings = {
            **kinto.core.DEFAULT_SETTINGS,
            "statsd_url": "udp://host:8080",
            "multiauth.policies": "basicauth",
        }
        self.config = Configurator(settings=settings)
        self.config.registry.storage = {}
        self.config.registry.cache = {}
        self.config.registry.permission = {}

        patch = mock.patch("kinto.plugins.statsd.StatsDService")
        self.mocked = patch.start()
        self.addCleanup(patch.stop)

    def test_statsd_is_set_on_cache(self):
        self.config.include("kinto.plugins.statsd")
        c = self.config.registry.metrics
        c.watch_execution_time.assert_any_call({}, prefix="backend")

    def test_statsd_is_set_on_storage(self):
        self.config.include("kinto.plugins.statsd")
        c = self.config.registry.metrics
        c.watch_execution_time.assert_any_call({}, prefix="backend")

    def test_statsd_is_set_on_permission(self):
        self.config.include("kinto.plugins.statsd")
        c = self.config.registry.metrics
        c.watch_execution_time.assert_any_call({}, prefix="backend")

    def test_statsd_is_set_on_authentication(self):
        self.config.include("kinto.plugins.statsd")
        c = self.config.registry.metrics
        c.watch_execution_time.assert_any_call(None, prefix="authentication")

    def test_statsd_counts_nothing_on_anonymous_requests(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/")
        self.assertFalse(self.mocked.count.called)

    def test_statsd_counts_views_and_methods(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/__heartbeat__")
        self.mocked().count.assert_any_call("view.heartbeat.GET")

    def test_statsd_counts_unknown_urls(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        app.get("/v0/coucou", status=404)
        self.assertFalse(self.mocked.count.called)

    @mock.patch("kinto.core.utils.hmac_digest")
    def test_statsd_counts_unique_users(self, digest_mocked):
        digest_mocked.return_value = "mat"
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        headers = {"Authorization": "Basic bWF0Og=="}
        app.get("/v0/", headers=headers)
        self.mocked().count.assert_any_call("users", unique="basicauth.mat")

    def test_statsd_counts_authentication_types(self):
        kinto.core.initialize(self.config, "0.0.1", "settings_prefix")
        app = webtest.TestApp(self.config.make_wsgi_app())
        headers = {"Authorization": "Basic bWF0Og=="}
        app.get("/v0/", headers=headers)
        self.mocked().count.assert_any_call("authn_type.basicauth")


class TestedClass:
    attribute = 3.14

    def test_method(self):
        pass

    def _private_method(self):
        pass


class StatsDMissing(unittest.TestCase):
    def setUp(self):
        self.previous = statsd.statsd_module
        statsd.statsd_module = None

    def tearDown(self):
        statsd.statsd_module = self.previous

    def test_client_instantiation_raises_properly(self):
        with self.assertRaises(ConfigurationError):
            statsd.load_from_config(mock.MagicMock())


@skip_if_no_statsd
class StatsdClientTest(unittest.TestCase):
    settings = {"statsd_url": "udp://foo:1234", "statsd_prefix": "prefix", "project_name": ""}

    def setUp(self):
        self.client = statsd.StatsDService("localhost", 1234, "prefix")
        self.test_object = TestedClass()

        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.watch_execution_time(self.test_object, prefix="test")
            self.mocked_client = mocked_client

    def test_public_methods_generates_statsd_calls(self):
        self.test_object.test_method()

        self.mocked_client.timer.assert_called_with("test.testedclass.test_method")

    def test_private_methods_does_not_generates_statsd_calls(self):
        self.mocked_client.reset_mock()
        self.test_object._private_method()
        self.assertFalse(self.mocked_client.timer.called)

    def test_count_increments_the_counter_for_key(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.count("click")
            mocked_client.incr.assert_called_with("click", count=1)

    def test_count_can_increment_by_more_than_one(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.count("click", count=10)
            mocked_client.incr.assert_called_with("click", count=10)

    def test_count_with_unique_uses_sets_for_key(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.count("click", unique="menu")
            mocked_client.set.assert_called_with("click", "menu")

    @mock.patch("kinto.plugins.statsd.statsd_module")
    def test_load_from_config(self, module_mock):
        config = testing.setUp()
        config.registry.settings = self.settings
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with("foo", 1234, prefix="prefix")

    @mock.patch("kinto.plugins.statsd.statsd_module")
    def test_load_from_config_uses_project_name_if_defined(self, module_mock):
        config = testing.setUp()
        config.registry.settings = {**self.settings, "project_name": "projectname"}
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with("foo", 1234, prefix="projectname")

    def test_statsd_count_handle_unconfigured_statsd_client(self):
        request = mock.MagicMock()
        request.registry.metrics = None
        statsd.statsd_count(request, "toto")  # Doesn't raise

    def test_statsd_count_call_the_client_if_configured(self):
        request = mock.MagicMock()
        request.registry.metrics = self.mocked_client
        statsd.statsd_count(request, "toto")
        self.mocked_client.count.assert_called_with("toto")


@skip_if_no_statsd
class TimingTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, *args, **kwargs):
        settings = super().get_app_settings(*args, **kwargs)
        if not statsd.statsd_module:
            return settings

        settings["statsd_url"] = "udp://localhost:8125"
        return settings

    def test_statds_tracks_listeners_execution_duration(self):
        statsd_client = self.app.app.registry.metrics._client
        with mock.patch.object(statsd_client, "timing") as mocked:
            self.app.get("/", headers=self.headers)
            self.assertTrue(mocked.called)

    def test_statds_tracks_authentication_policies(self):
        statsd_client = self.app.app.registry.metrics._client
        with mock.patch.object(statsd_client, "timing") as mocked:
            self.app.get("/", headers=self.headers)
            timers = set(c[0][0] for c in mocked.call_args_list)
            self.assertIn("authentication.basicauth.unauthenticated_userid", timers)
