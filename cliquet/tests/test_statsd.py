import mock

from pyramid import testing

from cliquet.tests.support import unittest
from cliquet import statsd


class StatsdClientTest(unittest.TestCase):
    settings = {'cliquet.statsd_url': 'udp://foo:1234'}

    def setUp(self):
        self.client = statsd.Client('localhost', 1234)
        with mock.patch.object(self.client, '_client') as mocked_client:
            class TestedClass(object):
                attribute = 3.14

                def test_method(self):
                    pass

                def _private_method(self):
                    pass

            self.test_object = TestedClass()
            self.client.watch_execution_time(self.test_object, prefix='test')
            self.mocked_client = mocked_client

    def test_public_methods_generates_statsd_calls(self):
        self.test_object.test_method()

        self.mocked_client.timer.assert_called_with(
            'test.testedclass.test_method')

    def test_private_methods_does_not_generates_statsd_calls(self):
        self.test_object._private_method()
        self.mocked_client.timer.assert_not_called()

    @mock.patch('cliquet.statsd.statsd_module')
    def test_load_from_config(self, module_mock):
        config = testing.setUp()
        config.registry.settings = self.settings
        statsd.load_from_config(config)
        module_mock.StatsClient.assert_called_with('foo', 1234)
