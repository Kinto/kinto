import types
import warnings
from urllib.parse import urlparse

from pyramid.events import NewResponse
from pyramid.exceptions import ConfigurationError
from pyramid.interfaces import IAuthenticationPolicy
from pyramid_multiauth import MultiAuthenticationPolicy

from kinto.core import utils


try:
    import statsd as statsd_module
except ImportError:  # pragma: no cover
    statsd_module = None


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

    def count(self, key, count=1, unique=None):
        if unique is None:
            return self._client.incr(key, count=count)
        else:
            return self._client.set(key, unique)


def statsd_count(request, count_key):
    metrics = request.registry.metrics
    if metrics:
        metrics.count(count_key)


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


def deprecated_registry(self):
    warnings.warn(
        "``config.registry.statsd`` is now deprecated. Check release notes.",
        DeprecationWarning,
    )
    return self.metrics


def includeme(config):
    settings = config.get_settings()
    config.registry.metrics = None

    if not settings["statsd_url"]:
        return

    statsd_mod = settings["statsd_backend"]
    statsd_mod = config.maybe_dotted(statsd_mod)
    client = statsd_mod.load_from_config(config)
    config.registry.metrics = client

    config.registry.__class__.statsd = property(deprecated_registry)

    client.watch_execution_time(config.registry.cache, prefix="backend")
    client.watch_execution_time(config.registry.storage, prefix="backend")
    client.watch_execution_time(config.registry.permission, prefix="backend")

    # Commit so that configured policy can be queried.
    config.commit()
    policy = config.registry.queryUtility(IAuthenticationPolicy)
    if isinstance(policy, MultiAuthenticationPolicy):
        for name, subpolicy in policy.get_policies():
            client.watch_execution_time(subpolicy, prefix="authentication", classname=name)
    else:
        client.watch_execution_time(policy, prefix="authentication")

    def on_new_response(event):
        request = event.request

        # Count unique users.
        user_id = request.prefixed_userid
        if user_id:
            # Get rid of colons in metric packet (see #1282).
            user_id = user_id.replace(":", ".")
            client.count("users", unique=user_id)

        # Count authentication verifications.
        if hasattr(request, "authn_type"):
            client.count(f"authn_type.{request.authn_type}")

        # Count view calls.
        service = request.current_service
        if service:
            client.count(f"view.{service.name}.{request.method}")

    config.add_subscriber(on_new_response, NewResponse)
