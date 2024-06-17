from unittest import mock

from pyramid import testing
from pyramid.exceptions import ConfigurationError

from kinto.core import statsd
from kinto.core.testing import skip_if_no_statsd, unittest

from .support import BaseWebTest


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
        self.client = statsd.Client("localhost", 1234, "prefix")
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

    @mock.patch("kinto.core.statsd.statsd_module")
    def test_load_from_config(self, module_mock):
        config = testing.setUp()
        config.registry.settings = self.settings
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with("foo", 1234, prefix="prefix")

    @mock.patch("kinto.core.statsd.statsd_module")
    def test_load_from_config_uses_project_name_if_defined(self, module_mock):
        config = testing.setUp()
        config.registry.settings = {**self.settings, "project_name": "projectname"}
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with("foo", 1234, prefix="projectname")

    def test_statsd_count_handle_unconfigured_statsd_client(self):
        request = mock.MagicMock()
        request.registry.statsd = None
        statsd.statsd_count(request, "toto")  # Doesn't raise

    def test_statsd_count_call_the_client_if_configured(self):
        request = mock.MagicMock()
        request.registry.statsd = self.mocked_client
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
        statsd_client = self.app.app.registry.statsd._client
        with mock.patch.object(statsd_client, "timing") as mocked:
            self.app.get("/", headers=self.headers)
            self.assertTrue(mocked.called)

    def test_statds_tracks_authentication_policies(self):
        statsd_client = self.app.app.registry.statsd._client
        with mock.patch.object(statsd_client, "timing") as mocked:
            self.app.get("/", headers=self.headers)
            timers = set(c[0][0] for c in mocked.call_args_list)
            self.assertIn("authentication.basicauth.unauthenticated_userid", timers)


### ADDITIONAL TEST CASES ###

@mock.patch("kinto.core.statsd.statsd_module")
class AdditionalStatsdClientTest(unittest.TestCase):
    def setUp(self):
        self.settings_with_project_name = {
            "statsd_url": "udp://foo:1234",
            "statsd_prefix": "prefix",
            "project_name": "projectname"
        }
        self.settings_without_project_name = {
            "statsd_url": "udp://foo:1234",
            "statsd_prefix": "prefix",
            "project_name": ""
        }

    ### ADDED TEST CASES FOR watch_execution_time FUNCTION ###
    def test_watch_execution_time_decorates_public_method(self, module_mock):
        ## INPUT ##
        client = statsd.Client("localhost", 1234, "prefix")
        test_object = TestedClass()

        with mock.patch.object(client, "_client") as mocked_client:
            client.watch_execution_time(test_object, prefix="test")
            test_object.test_method()
            ## ASSERT ##
            mocked_client.timer.assert_called_with("test.testedclass.test_method")
    
    ### ADDED TEST CASES FOR load_from_config FUNCTION ###
    def test_load_from_config_with_project_name(self, module_mock):
        ## INPUT ##
        config = testing.setUp()
        config.registry.settings = self.settings_with_project_name
        statsd.load_from_config(config)
        ## ASSERT ##
        module_mock.StatsClient.assert_called_with("foo", 1234, prefix="projectname")

    def test_load_from_config_without_project_name(self, module_mock):
        ## INPUT ##
        config = testing.setUp()
        config.registry.settings = self.settings_without_project_name
        statsd.load_from_config(config)
        ## ASSERT ##
        module_mock.StatsClient.assert_called_with("foo", 1234, prefix="prefix")
