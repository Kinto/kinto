import mock

from pyramid import testing

from cliquet.tests.support import unittest
from cliquet import statsd


class TestedClass(object):
    attribute = 3.14

    def test_method(self):
        pass

    def _private_method(self):
        pass


class StatsdClientTest(unittest.TestCase):
    settings = {
        'cliquet.statsd_url': 'udp://foo:1234',
        'cliquet.statsd_prefix': 'prefix',
        'cliquet.project_name': '',
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
        self.test_object._private_method()
        self.mocked_client.timer.assert_not_called()

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
        config.registry.settings['cliquet.project_name'] = 'projectname'
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with('foo', 1234,
                                                   prefix='projectname')
