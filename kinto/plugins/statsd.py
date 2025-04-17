import warnings
from datetime import timedelta
from urllib.parse import urlparse

from pyramid.exceptions import ConfigurationError
from zope.interface import implementer

from kinto.core import metrics


try:
    import statsd as statsd_module
except ImportError:  # pragma: no cover
    statsd_module = None


def sanitize(value):
    """
    Telegraf does not support ':' in values.
    See https://github.com/influxdata/telegraf/issues/4495
    """
    return value.replace(":", "") if isinstance(value, str) else value


@implementer(metrics.IMetricsService)
class StatsDService:
    def __init__(self, host, port, prefix):
        self._client = statsd_module.StatsClient(host, port, prefix=prefix)

    def timer(self, key, value=None, labels=[]):
        if labels:
            # [("method", "get")] -> "method.get"
            key = f"{key}." + ".".join(f"{label[0]}.{sanitize(label[1])}" for label in labels)
        if value:
            value = timedelta(seconds=value)
            return self._client.timing(key, value)
        return self._client.timer(key)

    def observe(self, key, value, labels=[]):
        return self._client.gauge(key, sanitize(value))

    def count(self, key, count=1, unique=None):
        if unique is None:
            return self._client.incr(key, count=count)
        if isinstance(unique, list):
            # [("method", "get")] -> "method.get"
            # [("endpoint", "/"), ("method", "get")] -> "endpoint./.method.get"
            unique = ".".join(f"{label[0]}.{sanitize(label[1])}" for label in unique)
        else:
            warnings.warn(
                "`unique` parameter should be of type ``list[tuple[str, str]]``",
                DeprecationWarning,
            )
        return self._client.set(key, unique)


def load_from_config(config):
    # If this is called, it means that a ``statsd_url`` was specified in settings.
    # (see ``kinto.core.initialization``)
    # Raise a proper error if the ``statsd`` module is not installed.
    if statsd_module is None:
        error_msg = "Please install Kinto with monitoring dependencies (e.g. statsd package)"
        raise ConfigurationError(error_msg)

    settings = config.get_settings()
    uri = settings["statsd_url"]
    uri = urlparse(uri)

    if settings["project_name"] != "":
        prefix = settings["project_name"]
    else:
        prefix = settings["statsd_prefix"]

    return StatsDService(uri.hostname, uri.port, prefix)


def includeme(config):
    settings = config.get_settings()

    # TODO: this backend abstraction may not be required anymore.
    statsd_mod = settings["statsd_backend"]
    statsd_mod = config.maybe_dotted(statsd_mod)
    client = statsd_mod.load_from_config(config)

    config.registry.registerUtility(client, metrics.IMetricsService)
