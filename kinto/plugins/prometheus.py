import functools
from time import perf_counter as time_now

from pyramid.exceptions import ConfigurationError


try:
    import prometheus_client as prometheus_module
except ImportError:  # pragma: no cover
    prometheus_module = None


from zope.interface import implementer

from kinto.core import metrics


_METRICS = {}


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
        if self._start_time is None:
            raise RuntimeError("Timer has not started.")
        dt_ms = 1000.0 * (time_now() - self._start_time)
        self.summary.observe(dt_ms)
        return self


@implementer(metrics.IMetricsService)
class PrometheusService:
    def __init__(self):
        pass

    def timer(self, key):
        global _METRICS
        if self.key not in _METRICS:
            _METRICS[self.key] = prometheus_module.Summary(key, f"Summary of {self.key}")
        return Timer(_METRICS[self.key])

    def count(self, key, count=None, unique=None):
        global _METRICS
        if key not in _METRICS:
            _METRICS[key] = prometheus_module.Counter(key, f"Counter of {key}")
        _METRICS[key].inc(count)

        # TODO: notion of "uniqueness"


def metrics_view(request):
    request.response.headers["Content-Type"] = prometheus_module.CONTENT_TYPE_LATEST

    registry = prometheus_module.CollectorRegistry()
    data = prometheus_module.generate_latest(registry)
    return [data]


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

    config.add_route("prometheus_metrics", "/__metrics__/")
    config.add_view(metrics_view, route_name="prometheus_metrics")
