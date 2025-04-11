import functools
import logging
import os
import shutil
import warnings
from time import perf_counter as time_now

from pyramid.events import ApplicationCreated
from pyramid.exceptions import ConfigurationError
from pyramid.response import Response
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

            # Ref: https://prometheus.github.io/client_python/multiprocess/
            _REGISTRY = prometheus_module.CollectorRegistry()
            multiprocess.MultiProcessCollector(_REGISTRY)
        else:
            _REGISTRY = prometheus_module.REGISTRY
    return _REGISTRY


def _fix_metric_name(s):
    return s.replace("-", "_").replace(".", "_").replace(" ", "_")


class Timer:
    def __init__(self, summary):
        self.summary = summary
        self._start_time = None

    def __call__(self, f):
        @safe_wraps(f)
        def _wrapped(*args, **kwargs):
            start_time = time_now()
            try:
                return f(*args, **kwargs)
            finally:
                dt_ms = 1000.0 * (time_now() - start_time)
                self.summary.observe(dt_ms)

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
        dt_ms = 1000.0 * (time_now() - self._start_time)
        self.summary.observe(dt_ms)
        return self


@implementer(metrics.IMetricsService)
class PrometheusService:
    def __init__(self, prefix=""):
        prefix_clean = ""
        if prefix:
            # In GCP Console, the metrics are grouped by the first
            # word before the first underscore. Here we make sure the specified
            # prefix is not mixed up with metrics names.
            # (eg. `remote-settings` -> `remotesettings_`, `kinto_` -> `kinto_`)
            prefix_clean = _fix_metric_name(prefix).replace("_", "") + "_"
        self.prefix = prefix_clean.lower()

    def timer(self, key):
        global _METRICS
        key = self.prefix + key

        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Summary(
                _fix_metric_name(key), f"Summary of {key}", registry=get_registry()
            )

        if not isinstance(_METRICS[key], prometheus_module.Summary):
            raise RuntimeError(
                f"Metric {key} already exists with different type ({_METRICS[key]})"
            )

        return Timer(_METRICS[key])

    def observe(self, key, value, labels=[]):
        global _METRICS
        key = self.prefix + key

        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Summary(
                _fix_metric_name(key),
                f"Summary of {key}",
                labelnames=[label_name for label_name, _ in labels],
                registry=get_registry(),
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
        key = self.prefix + key

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

        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Counter(
                _fix_metric_name(key),
                f"Counter of {key}",
                labelnames=[label_name for label_name, _ in labels],
                registry=get_registry(),
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


def _reset_multiproc_folder_content(path, _evt):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)


def includeme(config):
    if prometheus_module is None:
        error_msg = (
            "Please install Kinto with monitoring dependencies (e.g. prometheus-client package)"
        )
        raise ConfigurationError(error_msg)

    config.add_api_capability(
        "prometheus",
        description="Prometheus metrics.",
        url="https://github.com/Kinto/kinto/",
    )

    config.add_route("prometheus_metrics", "/__metrics__")
    config.add_view(metrics_view, route_name="prometheus_metrics")

    # Reinitialize the registry on initialization.
    # This is mainly useful in tests, where the plugin is included
    # several times with different settings.
    registry = get_registry()

    # Empty multiproc folder content on startup.
    if PROMETHEUS_MULTIPROC_DIR:  # pragma: no cover
        config.add_subscriber(
            functools.partial(_reset_multiproc_folder_content, PROMETHEUS_MULTIPROC_DIR),
            ApplicationCreated,
        )
    else:
        logger.warning("Prometheus metrics will run in single-process mode only.")

    for collector in _METRICS.values():
        try:
            registry.unregister(collector)
        except KeyError:  # pragma: no cover
            pass
    _METRICS.clear()

    settings = config.get_settings()
    prefix = settings.get("prometheus_prefix", settings["project_name"])

    config.registry.registerUtility(PrometheusService(prefix=prefix), metrics.IMetricsService)
