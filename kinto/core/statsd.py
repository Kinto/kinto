import types

try:
    import statsd as statsd_module
except ImportError:  # pragma: no cover
    statsd_module = None

from pyramid.exceptions import ConfigurationError
from urllib.parse import urlparse

from kinto.core import utils


class Client:
    def __init__(self, host, port, prefix):
        self._client = statsd_module.StatsClient(host, port, prefix=prefix)

    def watch_execution_time(self, obj, prefix="", classname=None):
        classname = classname or utils.classname(obj)
        members = dir(obj)
        for name in members:
            value = getattr(obj, name)
            is_method = isinstance(value, types.MethodType)
            if not name.startswith("_") and is_method:
                statsd_key = f"{prefix}.{classname}.{name}"
                decorated_method = self.timer(statsd_key)(value)
                setattr(obj, name, decorated_method)

    def timer(self, key):
        return self._client.timer(key)

    def count(self, key, unique=None):
        if unique is None:
            return self._client.incr(key, count=1)
        else:
            return self._client.set(key, unique)


def statsd_count(request, count_key):
    statsd = request.registry.statsd
    if statsd:
        statsd.count(count_key)


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

    return Client(uri.hostname, uri.port, prefix)
