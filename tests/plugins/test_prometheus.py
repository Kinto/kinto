import functools
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


@skip_if_no_prometheus
class ViewsTest(PrometheusWebTest):
    def test_prometheus_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("prometheus", capabilities)

    def test_endpoint_with_metrics(self):
        self.app.put("/buckets/test", headers=get_user_headers("aaa"))

        resp = self.app.get("/__metrics__")
        self.assertIn("Summary", resp.text)


def my_func(a, b):
    return a + b


@skip_if_no_prometheus
class ServiceTest(PrometheusWebTest):
    def test_timer_can_be_used_as_context_manager(self):
        with self.app.app.registry.metrics.timer("func.latency.context"):
            self.assertEqual(my_func(1, 1), 2)

        resp = self.app.get("/__metrics__")
        self.assertIn("TYPE func_latency_context summary", resp.text)

    def test_timer_can_be_used_as_decorator(self):
        decorated = self.app.app.registry.metrics.timer("func.latency.decorator")(my_func)

        self.assertEqual(decorated(1, 1), 2)

        resp = self.app.get("/__metrics__")
        self.assertIn("TYPE func_latency_decorator summary", resp.text)

    def test_timer_can_be_used_as_decorator_on_partial_function(self):
        partial = functools.partial(my_func, 3)
        decorated = self.app.app.registry.metrics.timer("func.latency.partial")(partial)

        self.assertEqual(decorated(3), 6)

        resp = self.app.get("/__metrics__")
        self.assertIn("TYPE func_latency_partial summary", resp.text)

    def test_observe_a_single_value(self):
        self.app.app.registry.metrics.observe("price", 111)

        resp = self.app.get("/__metrics__")
        self.assertIn("price_sum 111", resp.text)

    def test_observe_a_single_value_with_labels(self):
        self.app.app.registry.metrics.observe("size", 3.14, labels=[("endpoint", "/buckets")])

        resp = self.app.get("/__metrics__")
        self.assertIn('size_sum{endpoint="/buckets"} 3.14', resp.text)

    def test_count_by_key(self):
        self.app.app.registry.metrics.count("key")

        resp = self.app.get("/__metrics__")
        self.assertIn("key_total 1.0", resp.text)

    def test_count_by_key_value(self):
        self.app.app.registry.metrics.count("bigstep", count=2)

        resp = self.app.get("/__metrics__")
        self.assertIn("bigstep_total 2.0", resp.text)

    def test_count_by_key_grouped(self):
        self.app.app.registry.metrics.count("http", unique=[("status", "500")])
        self.app.app.registry.metrics.count("http", unique=[("status", "200")])

        resp = self.app.get("/__metrics__")
        self.assertIn('http_total{status="500"} 1.0', resp.text)
        self.assertIn('http_total{status="200"} 1.0', resp.text)

    def test_metrics_cant_be_mixed(self):
        self.app.app.registry.metrics.count("counter")
        with self.assertRaises(RuntimeError):
            self.app.app.registry.metrics.timer("counter")

        self.app.app.registry.metrics.timer("timer")
        with self.assertRaises(RuntimeError):
            self.app.app.registry.metrics.count("timer")

        self.app.app.registry.metrics.count("observer")
        with self.assertRaises(RuntimeError):
            self.app.app.registry.metrics.observe("observer", 42)

    def test_metrics_names_and_labels_are_transformed(self):
        self.app.app.registry.metrics.count("http.home.status", unique=[("code.get", "200")])

        resp = self.app.get("/__metrics__")
        self.assertIn('http_home_status_total{code_get="200"} 1.0', resp.text)

    def test_count_with_legacy_string_generic_group(self):
        self.app.app.registry.metrics.count("champignons", unique="boletus")

        resp = self.app.get("/__metrics__")
        self.assertIn('champignons_total{group="boletus"} 1.0', resp.text)

    def test_count_with_legacy_string_basic_group(self):
        self.app.app.registry.metrics.count("mushrooms", unique="species.boletus")

        resp = self.app.get("/__metrics__")
        self.assertIn('mushrooms_total{species="boletus"} 1.0', resp.text)
