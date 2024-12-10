from unittest import mock

from pyramid import testing
from pyramid.exceptions import ConfigurationError

from kinto.core.testing import skip_if_no_statsd, unittest
from kinto.plugins import statsd


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

        patch = mock.patch.object(self.client, "_client")
        self.mocked_client = patch.start()
        self.addCleanup(patch.stop)

    def test_observe_a_single_value(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.observe("size", 3.14)
            mocked_client.gauge.assert_called_with("size", 3.14)

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

    def test_count_turns_tuples_into_set_key(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.count("click", unique=[("component", "menu")])
            mocked_client.set.assert_called_with("click", "component.menu")

    def test_count_turns_multiple_tuples_into_one_set_key(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.count("click", unique=[("component", "menu"), ("sound", "off")])
            mocked_client.set.assert_called_with("click", "component.menu.sound.off")

    def test_values_are_sanitized(self):
        with mock.patch.object(self.client, "_client") as mocked_client:
            self.client.count("click", unique=[("user", "account:boss")])
            mocked_client.set.assert_called_with("click", "user.accountboss")

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
