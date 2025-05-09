import logging
import os
import shutil
import warnings
from time import perf_counter as time_now

from pyramid.exceptions import ConfigurationError
from pyramid.response import Response
from pyramid.settings import asbool, aslist
from zope.interface import implementer

from kinto.core import metrics
from kinto.core.utils import safe_wraps


try:
    import prometheus_client as prometheus_module
except ImportError:  # pragma: no cover
    prometheus_module = None


logger = logging.getLogger(__name__)

_METRICS = {}
_REGISTRY = None


PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR")


def get_registry():
    global _REGISTRY

    if _REGISTRY is None:
        if PROMETHEUS_MULTIPROC_DIR:  # pragma: no cover
            from prometheus_client import multiprocess

            _reset_multiproc_folder_content()
            # Ref: https://prometheus.github.io/client_python/multiprocess/
            _REGISTRY = prometheus_module.CollectorRegistry()
            multiprocess.MultiProcessCollector(_REGISTRY)
        else:
            _REGISTRY = prometheus_module.REGISTRY
            logger.warning("Prometheus metrics will run in single-process mode only.")
    return _REGISTRY


def _fix_metric_name(s):
    return s.replace("-", "_").replace(".", "_").replace(" ", "_")


class Timer:
    """
    A decorator to time the execution of a function. It will use the
    `prometheus_client.Histogram` to record the time taken by the function
    in seconds. The histogram is passed as an argument to the
    constructor.

    Main limitation: it does not support `labels` on the decorator.
    """

    def __init__(self, histogram):
        self.histogram = histogram
        self._start_time = None

    def set_labels(self, labels):
        if not labels:
            return
        self.histogram = self.histogram.labels(*(label_value for _, label_value in labels))

    def observe(self, value):
        return self.histogram.observe(value)

    def __call__(self, f):
        @safe_wraps(f)
        def _wrapped(*args, **kwargs):
            start_time = time_now()
            try:
                return f(*args, **kwargs)
            finally:
                dt_sec = time_now() - start_time
                self.histogram.observe(dt_sec)

        return _wrapped

    def __enter__(self):
        return self.start()

    def __exit__(self, typ, value, tb):
        self.stop()

    def start(self):
        self._start_time = time_now()
        return self

    def stop(self):
        if self._start_time is None:  # pragma: nocover
            raise RuntimeError("Timer has not started.")
        dt_sec = time_now() - self._start_time
        self.histogram.observe(dt_sec)
        return self


class NoOpHistogram:  # pragma: no cover
    def observe(self, value):
        pass

    def labels(self, *args):
        return self


@implementer(metrics.IMetricsService)
class PrometheusService:
    def __init__(self, prefix="", disabled_metrics=[], histogram_buckets=None):
        prefix_clean = ""
        if prefix:
            # In GCP Console, the metrics are grouped by the first
            # word before the first underscore. Here we make sure the specified
            # prefix is not mixed up with metrics names.
            # (eg. `remote-settings` -> `remotesettings_`, `kinto_` -> `kinto_`)
            prefix_clean = _fix_metric_name(prefix).replace("_", "") + "_"
        self.prefix = prefix_clean.lower()
        self.disabled_metrics = [m.replace(self.prefix, "") for m in disabled_metrics]
        self.histogram_buckets = histogram_buckets

    def timer(self, key, value=None, labels=[]):
        global _METRICS

        key = _fix_metric_name(key)
        if key in self.disabled_metrics:
            return Timer(histogram=NoOpHistogram())

        key = self.prefix + key
        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Histogram(
                key,
                f"Histogram of {key}",
                labelnames=[label_name for label_name, _ in labels],
                buckets=self.histogram_buckets,
            )

        if not isinstance(_METRICS[key], prometheus_module.Histogram):
            raise RuntimeError(
                f"Metric {key} already exists with different type ({_METRICS[key]})"
            )

        timer = Timer(histogram=_METRICS[key])
        timer.set_labels(labels)

        if value is not None:
            # We are timing something.
            return timer.observe(value)

        # We are not timing anything, just returning the timer object
        # (eg. to be used as decorator or context manager).
        # Note that in this case, the labels values will be the same for all calls.
        return timer

    def observe(self, key, value, labels=[]):
        global _METRICS

        key = _fix_metric_name(key)
        if key in self.disabled_metrics:
            return

        key = self.prefix + key
        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Summary(
                key,
                f"Summary of {key}",
                labelnames=[label_name for label_name, _ in labels],
            )

        if not isinstance(_METRICS[key], prometheus_module.Summary):
            raise RuntimeError(
                f"Metric {key} already exists with different type ({_METRICS[key]})"
            )

        m = _METRICS[key]
        if labels:
            m = m.labels(*(label_value for _, label_value in labels))

        m.observe(value)

    def count(self, key, count=1, unique=None):
        global _METRICS

        key = _fix_metric_name(key)
        if key in self.disabled_metrics:
            return

        labels = []
        if unique:
            if isinstance(unique, str):
                warnings.warn(
                    "`unique` parameter should be of type ``list[tuple[str, str]]``",
                    DeprecationWarning,
                )
                # Turn `unique` into a group and a value:
                # "bob" -> "group.bob"
                # "method.basicauth.mat" -> [("method_basicauth", "mat")]`
                if "." not in unique:
                    unique = f"group.{unique}"
                label_name, label_value = unique.rsplit(".", 1)
                unique = [(label_name, label_value)]

            labels = [
                (_fix_metric_name(label_name), label_value) for label_name, label_value in unique
            ]

        key = self.prefix + key
        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Counter(
                key,
                f"Counter of {key}",
                labelnames=[label_name for label_name, _ in labels],
            )

        if not isinstance(_METRICS[key], prometheus_module.Counter):
            raise RuntimeError(
                f"Metric {key} already exists with different type ({_METRICS[key]})"
            )

        m = _METRICS[key]
        if labels:
            m = m.labels(*(label_value for _, label_value in labels))

        m.inc(count)


def metrics_view(request):
    registry = get_registry()
    data = prometheus_module.generate_latest(registry)
    resp = Response(body=data)
    resp.headers["Content-Type"] = prometheus_module.CONTENT_TYPE_LATEST
    resp.headers["Content-Length"] = str(len(data))
    return resp


def _reset_multiproc_folder_content():  # pragma: no cover
    shutil.rmtree(PROMETHEUS_MULTIPROC_DIR, ignore_errors=True)
    os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)


def reset_registry():
    # This is mainly useful in tests, where the plugin is included
    # several times with different settings.
    registry = get_registry()

    for collector in _METRICS.values():
        try:
            registry.unregister(collector)
        except KeyError:  # pragma: no cover
            pass
    _METRICS.clear()


def includeme(config):
    if prometheus_module is None:
        error_msg = (
            "Please install Kinto with monitoring dependencies (e.g. prometheus-client package)"
        )
        raise ConfigurationError(error_msg)

    settings = config.get_settings()

    if not asbool(settings.get("prometheus_created_metrics_enabled", True)):
        prometheus_module.disable_created_metrics()

    prefix = settings.get("prometheus_prefix", settings["project_name"])
    disabled_metrics = aslist(settings.get("prometheus_disabled_metrics", ""))

    # Default buckets for histogram metrics are (.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, INF)
    # we reduce it from 15 to 8 values by default here, and let the user override it if needed.
    histogram_buckets_values = aslist(
        settings.get(
            "prometheus_histogram_buckets", "0.01 0.05 0.1 0.5 1.0 3.0 6.0 Inf"
        )  # Note: Inf is added by default.
    )
    histogram_buckets = [float(x) for x in histogram_buckets_values]
    # Note: we don't need to check for INF or list size, it's done in the prometheus_client library.

    get_registry()  # Initialize the registry.

    metrics_impl = PrometheusService(
        prefix=prefix, disabled_metrics=disabled_metrics, histogram_buckets=histogram_buckets
    )

    config.add_api_capability(
        "prometheus",
        description="Prometheus metrics.",
        url="https://github.com/Kinto/kinto/",
        prefix=metrics_impl.prefix,
        disabled_metrics=disabled_metrics,
    )

    config.add_route("prometheus_metrics", "/__metrics__")
    config.add_view(metrics_view, route_name="prometheus_metrics")

    config.registry.registerUtility(metrics_impl, metrics.IMetricsService)
