import mock

from pyramid import testing

from cliquet.tests.support import unittest, BaseWebTest
from cliquet import statsd


class TestedClass(object):
    attribute = 3.14

    def test_method(self):
        pass

    def _private_method(self):
        pass


@unittest.skipIf(not statsd.statsd_module, "statsd is not installed.")
class StatsdClientTest(unittest.TestCase):
    settings = {
        'statsd_url': 'udp://foo:1234',
        'statsd_prefix': 'prefix',
        'project_name': '',
    }

    def setUp(self):
        self.client = statsd.Client('localhost', 1234, 'prefix')
        self.test_object = TestedClass()

        with mock.patch.object(self.client, '_client') as mocked_client:
            self.client.watch_execution_time(self.test_object, prefix='test')
            self.mocked_client = mocked_client

    def test_public_methods_generates_statsd_calls(self):
        self.test_object.test_method()

        self.mocked_client.timer.assert_called_with(
            'test.testedclass.test_method')

    def test_private_methods_does_not_generates_statsd_calls(self):
        self.mocked_client.reset_mock()
        self.test_object._private_method()
        self.assertFalse(self.mocked_client.timer.called)

    def test_count_increments_the_counter_for_key(self):
        with mock.patch.object(self.client, '_client') as mocked_client:
            self.client.count('click')
            mocked_client.incr.assert_called_with('click', count=1)

    def test_count_with_unique_uses_sets_for_key(self):
        with mock.patch.object(self.client, '_client') as mocked_client:
            self.client.count('click', unique='menu')
            mocked_client.set.assert_called_with('click', 'menu')

    @mock.patch('cliquet.statsd.statsd_module')
    def test_load_from_config(self, module_mock):
        config = testing.setUp()
        config.registry.settings = self.settings
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with('foo', 1234,
                                                   prefix='prefix')

    @mock.patch('cliquet.statsd.statsd_module')
    def test_load_from_config_uses_project_name_if_defined(self, module_mock):
        config = testing.setUp()
        config.registry.settings = self.settings.copy()
        config.registry.settings['project_name'] = 'projectname'
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with('foo', 1234,
                                                   prefix='projectname')

    def test_statsd_count_handle_unconfigured_statsd_client(self):
        request = mock.MagicMock()
        request.registry.statsd = None
        statsd.statsd_count(request, 'toto')  # Doesn't raise

    def test_statsd_count_call_the_client_if_configured(self):
        request = mock.MagicMock()
        request.registry.statsd = self.mocked_client
        statsd.statsd_count(request, 'toto')
        self.mocked_client.count.assert_called_with('toto')


@unittest.skipIf(not statsd.statsd_module, "statsd is not installed.")
class TimingTest(BaseWebTest, unittest.TestCase):
    def get_app_settings(self, *args, **kwargs):
        settings = super(TimingTest, self).get_app_settings(*args, **kwargs)
        if not statsd.statsd_module:
            return settings

        settings['statsd_url'] = 'udp://localhost:8125'
        return settings

    def test_statds_tracks_listeners_execution_duration(self):
        statsd_client = self.app.app.registry.statsd._client
        with mock.patch.object(statsd_client, 'timing') as mocked:
            self.app.get('/', headers=self.headers)
            self.assertTrue(mocked.called)

    def test_statds_tracks_authentication_policies(self):
        statsd_client = self.app.app.registry.statsd._client
        with mock.patch.object(statsd_client, 'timing') as mocked:
            self.app.get('/', headers=self.headers)
            timers = set(c[0][0] for c in mocked.call_args_list)
            self.assertIn('authentication.basicauth.unauthenticated_userid',
                          timers)
