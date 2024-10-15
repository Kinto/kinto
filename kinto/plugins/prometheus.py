import functools
from time import perf_counter as time_now

from pyramid.exceptions import ConfigurationError
from pyramid.response import Response
from zope.interface import implementer

from kinto.core import metrics


try:
    import prometheus_client as prometheus_module
except ImportError:  # pragma: no cover
    prometheus_module = None


_METRICS = {}
_REGISTRY = None


def get_registry():
    global _REGISTRY

    if _REGISTRY is None:
        _REGISTRY = prometheus_module.CollectorRegistry()
    return _REGISTRY


def _fix_metric_name(s):
    return s.replace("-", "_").replace(".", "_")


def safe_wraps(wrapper, *args, **kwargs):
    """Safely wraps partial functions."""
    while isinstance(wrapper, functools.partial):
        wrapper = wrapper.func
    return functools.wraps(wrapper, *args, **kwargs)


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
    def timer(self, key):
        global _METRICS
        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Summary(
                _fix_metric_name(key), f"Summary of {key}", registry=get_registry()
            )

        if not isinstance(_METRICS[key], prometheus_module.Summary):
            raise RuntimeError(
                f"Metric {key} already exists with different type ({_METRICS[key]})"
            )

        return Timer(_METRICS[key])

    def count(self, key, count=1, unique=None):
        global _METRICS

        # Turn `unique` into a group and a value:
        # eg. `method.basicauth.mat` -> `method_basicauth="mat"`
        label_value = None
        if unique:
            if "." not in unique:
                unique = f"group.{unique}"
            label_name, label_value = unique.rsplit(".", 1)
            label_names = (_fix_metric_name(label_name),)
        else:
            label_names = tuple()

        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Counter(
                _fix_metric_name(key),
                f"Counter of {key}",
                labelnames=label_names,
                registry=get_registry(),
            )

        if not isinstance(_METRICS[key], prometheus_module.Counter):
            raise RuntimeError(
                f"Metric {key} already exists with different type ({_METRICS[key]})"
            )

        m = _METRICS[key]
        if label_value is not None:
            m = m.labels(label_value)

        m.inc(count)


def metrics_view(request):
    registry = get_registry()
    data = prometheus_module.generate_latest(registry)
    resp = Response(body=data)
    resp.headers["Content-Type"] = prometheus_module.CONTENT_TYPE_LATEST
    resp.headers["Content-Length"] = str(len(data))
    return resp


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

    config.registry.registerUtility(PrometheusService(), metrics.IMetricsService)
