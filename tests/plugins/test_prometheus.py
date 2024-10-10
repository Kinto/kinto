import unittest
from unittest import mock

from pyramid.exceptions import ConfigurationError

from kinto.core.testing import get_user_headers, skip_if_no_prometheus
from kinto.plugins import prometheus

from .. import support


DATETIME_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}$"


class PrometheusMissing(unittest.TestCase):
    def setUp(self):
        self.previous = prometheus.prometheus_module
        prometheus.prometheus_module = None

    def tearDown(self):
        prometheus.prometheus_module = self.previous

    def test_client_instantiation_raises_properly(self):
        with self.assertRaises(ConfigurationError):
            prometheus.includeme(mock.MagicMock())


class PrometheusWebTest(support.BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.prometheus"
        return settings


class ViewsTest(PrometheusWebTest):
    def test_prometheus_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("prometheus", capabilities)

    def test_endpoint_with_metrics(self):
        self.app.put("/buckets/test", headers=get_user_headers("aaa"))

        resp = self.app.get("/__metrics__")
        self.assertIn("Summary", resp.text)


def test_func():
    pass


@skip_if_no_prometheus
class ServiceTest(PrometheusWebTest):
    def test_timer_can_be_used_as_context_manager(self):
        with self.app.app.registry.metrics.timer("func.latency"):
            test_func()

        resp = self.app.get("/__metrics__")
        self.assertIn("TODO", resp.text)

    def test_timer_can_be_used_as_decorator(self):
        decorated = self.app.app.registry.metrics.timer("func.latency")(test_func)

        decorated()

        resp = self.app.get("/__metrics__")
        self.assertIn("TODO", resp.text)

    def test_count_by_key(self):
        self.app.app.registry.metrics.count("key")

        resp = self.app.get("/__metrics__")
        self.assertIn("key_total 1.0", resp.text)

    def test_count_by_key_value(self):
        self.app.app.registry.metrics.count("key", count=2)

        resp = self.app.get("/__metrics__")
        self.assertIn("key_total 2.0", resp.text)

    def test_count_by_key_grouped(self):
        self.app.app.registry.metrics.count("members", unique="family.foo")
        self.app.app.registry.metrics.count("members", unique="family.bar")

        resp = self.app.get("/__metrics__")
        self.assertIn('members_total{family_foo="family_bar"} 1.0', resp.text)
