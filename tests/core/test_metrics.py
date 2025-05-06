import unittest
from unittest import mock

from pyramid.config import Configurator

from kinto.core import metrics


class TestedClass:
    attribute = 3.14

    def test_method(self):
        pass

    def _private_method(self):
        pass


class WatchExecutionTimeTest(unittest.TestCase):
    def setUp(self):
        self.test_object = TestedClass()
        self.mocked = mock.MagicMock()
        metrics.watch_execution_time(self.mocked, self.test_object, prefix="test")

    def test_public_methods_generates_statsd_calls(self):
        self.test_object.test_method()
        self.mocked.timer.assert_called_with(
            "test.testedclass.seconds", labels=[("method", "test_method")]
        )

    def test_private_methods_does_not_generates_statsd_calls(self):
        self.test_object._private_method()
        self.assertFalse(self.mocked().timer.called)


class ListenerWithTimerTest(unittest.TestCase):
    def setUp(self):
        self.config = Configurator()
        self.func = lambda x: x  # noqa: E731

    def test_without_metrics_service(self):
        wrapped = metrics.listener_with_timer(self.config, "key", self.func)

        self.assertEqual(wrapped(42), 42)  # does not raise

    def test_with_metrics_service(self):
        self.config.registry.registerUtility(mock.MagicMock(), metrics.IMetricsService)
        wrapped = metrics.listener_with_timer(self.config, "key", self.func)

        self.assertEqual(wrapped(42), 42)
        self.config.registry.metrics.timer.assert_called_with("key.seconds")
