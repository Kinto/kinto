import mock

from cliquet.tests.support import unittest
from cliquet import statsd


class StatsdMetaclassTest(unittest.TestCase):

    def setUp(self):
        with mock.patch('cliquet.statsd.Client') as mocked_client:
            class TestedClass(object):
                __metaclass__ = statsd.get_metaclass('test')

                def test_method(self):
                    pass

                def _private_method(self):
                    pass

            self.TestedClass = TestedClass
            self.mocked_client = mocked_client

    def test_public_methods_generates_statsd_calls(self):
        test_object = self.TestedClass()
        test_object.test_method()

        self.mocked_client.timer.assert_called_with(
            'test.testedclass.test_method')

    def test_private_methods_does_not_generates_statsd_calls(self):
        test_object = self.TestedClass()
        test_object._private_method()

        self.mocked_client.timer.assert_not_called()


class StatsdClientTest(unittest.TestCase):
    settings = {'cliquet.statsd_url': 'udp://foo:1234'}

    @mock.patch('cliquet.statsd.statsd_module')
    def test_setup_client_reads_the_settings(self, module_mock):
        statsd.Client.setup_client(self.settings)
        module_mock.StatsClient.assert_called_with('foo', 1234)

    @mock.patch('cliquet.statsd.statsd_module')
    def test_setup_client_setups_a_class_argument(self, module_mock):
        statsd.Client.setup_client(self.settings)
        self.assertIsNotNone(statsd.Client.statsd)
