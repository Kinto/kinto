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
    def setUp(self):
        super().setUp()
        prometheus.reset_registry()

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.prometheus"
        settings["project_name"] = "kinto PROD"
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
        self.assertIn("TYPE kintoprod_func_latency_context histogram", resp.text)

    def test_timer_can_be_used_as_decorator(self):
        decorated = self.app.app.registry.metrics.timer("func.latency.decorator")(my_func)

        self.assertEqual(decorated(1, 1), 2)

        resp = self.app.get("/__metrics__")
        self.assertIn("TYPE kintoprod_func_latency_decorator histogram", resp.text)

    def test_timer_can_be_used_as_decorator_on_partial_function(self):
        partial = functools.partial(my_func, 3)
        decorated = self.app.app.registry.metrics.timer("func.latency.partial")(partial)

        self.assertEqual(decorated(3), 6)

        resp = self.app.get("/__metrics__")
        self.assertIn("TYPE kintoprod_func_latency_partial histogram", resp.text)

    def test_observe_a_single_value(self):
        self.app.app.registry.metrics.observe("price", 111)

        resp = self.app.get("/__metrics__")
        self.assertIn("kintoprod_price_sum 111", resp.text)

    def test_observe_a_single_value_with_labels(self):
        self.app.app.registry.metrics.observe("size", 3.14, labels=[("endpoint", "/buckets")])

        resp = self.app.get("/__metrics__")
        self.assertIn('kintoprod_size_sum{endpoint="/buckets"} 3.14', resp.text)

    def test_count_by_key(self):
        self.app.app.registry.metrics.count("key")

        resp = self.app.get("/__metrics__")
        self.assertIn("kintoprod_key_total 1.0", resp.text)

    def test_count_by_key_value(self):
        self.app.app.registry.metrics.count("bigstep", count=2)

        resp = self.app.get("/__metrics__")
        self.assertIn("kintoprod_bigstep_total 2.0", resp.text)

    def test_count_by_key_grouped(self):
        self.app.app.registry.metrics.count("http", unique=[("status", "500")])
        self.app.app.registry.metrics.count("http", unique=[("status", "200")])

        resp = self.app.get("/__metrics__")
        self.assertIn('kintoprod_http_total{status="500"} 1.0', resp.text)
        self.assertIn('kintoprod_http_total{status="200"} 1.0', resp.text)

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
        self.assertIn('kintoprod_http_home_status_total{code_get="200"} 1.0', resp.text)

    def test_count_with_legacy_string_generic_group(self):
        self.app.app.registry.metrics.count("champignons", unique="boletus")

        resp = self.app.get("/__metrics__")
        self.assertIn('kintoprod_champignons_total{group="boletus"} 1.0', resp.text)

    def test_count_with_legacy_string_basic_group(self):
        self.app.app.registry.metrics.count("mushrooms", unique="species.boletus")

        resp = self.app.get("/__metrics__")
        self.assertIn('kintoprod_mushrooms_total{species="boletus"} 1.0', resp.text)


@skip_if_no_prometheus
class PrometheusNoPrefixTest(PrometheusWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["project_name"] = "Some Project"
        settings["prometheus_prefix"] = ""
        return settings

    def test_metrics_have_no_prefix(self):
        self.app.app.registry.metrics.observe("price", 111)

        resp = self.app.get("/__metrics__")
        self.assertIn("TYPE price summary", resp.text)


@skip_if_no_prometheus
class PrometheusNoCreatedTest(PrometheusWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["prometheus_created_metrics_enabled"] = "false"
        return settings

    def test_metrics_created_not_in_response(self):
        self.app.app.registry.metrics.observe("price", 111)

        resp = self.app.get("/__metrics__")

        self.assertIn("TYPE kintoprod_price summary", resp.text)
        self.assertNotIn("TYPE kintoprod_price_created summary", resp.text)


@skip_if_no_prometheus
class PrometheusDisabledMetricsTest(PrometheusWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["prometheus_disabled_metrics"] = "kintoprod_price kintoprod_key func_latency"
        return settings

    def test_disabled_etrics_not_in_response(self):
        self.app.app.registry.metrics.observe("price", 111)
        self.app.app.registry.metrics.count("key")
        self.app.app.registry.metrics.observe("size", 3.14, labels=[("endpoint", "/buckets")])
        decorated = self.app.app.registry.metrics.timer("func.latency")(my_func)
        decorated(1, 34)  # Call the function to trigger the timer and NoOpHistogram

        resp = self.app.get("/__metrics__")

        self.assertIn("TYPE kintoprod_size summary", resp.text)
        self.assertNotIn("TYPE kintoprod_key counter", resp.text)
        self.assertNotIn("TYPE kintoprod_price summary", resp.text)
        self.assertNotIn("TYPE kintoprod_func_latency histogram", resp.text)


@skip_if_no_prometheus
class PrometheusCustomTest(PrometheusWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["prometheus_histogram_buckets"] = "0.1 1 Inf"
        return settings

    def test_duration_metrics_only_contain_specified_buckets(self):
        self.app.app.registry.metrics.timer("func")(my_func)
        my_func(1, 34)

        resp = self.app.get("/__metrics__")

        self.assertEqual(resp.text.count("kintoprod_func_bucket"), 3)
        self.assertIn('kintoprod_func_bucket{le="0.1"}', resp.text)
        self.assertIn('kintoprod_func_bucket{le="1.0"}', resp.text)
        self.assertIn('kintoprod_func_bucket{le="+Inf"}', resp.text)
