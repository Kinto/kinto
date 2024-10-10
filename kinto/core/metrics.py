import types

from zope.interface import Interface

from kinto.core import utils


class IMetricsService(Interface):
    """
    An interface that defines the metrics service contract.
    Any class implementing this must provide all its methods.
    """

    def timer(key):
        """
        Watch execution time.
        """

    def count(key, count=1, unique=None):
        """
        Count occurrences. If `unique` is set, overwrites the counter value
        on each call.
        """


def watch_execution_time(metrics_service, obj, prefix="", classname=None):
    """
    Decorate all methods of an object in order to watch their execution time.
    Metrics will be named `{prefix}.{classname}.{method}`.
    """
    classname = classname or utils.classname(obj)
    members = dir(obj)
    for name in members:
        value = getattr(obj, name)
        is_method = isinstance(value, types.MethodType)
        if not name.startswith("_") and is_method:
            statsd_key = f"{prefix}.{classname}.{name}"
            decorated_method = metrics_service.timer(statsd_key)(value)
            setattr(obj, name, decorated_method)


def listener_with_timer(config, key, func):
    """
    Add a timer with the specified `key` on the specified `func`.
    This is used to avoid evaluating `config.registry.metrics` during setup time
    to avoid having to deal with initialization order and configuration committing.
    """

    def wrapped(*args, **kwargs):
        metrics_service = config.registry.metrics
        if not metrics_service:
            return func(*args, **kwargs)
        # If metrics are enabled, monitor execution time of listeners.
        with metrics_service.timer(key):
            return func(*args, **kwargs)

    return wrapped
