import types
from collections.abc import Callable
from typing import Any

from pyramid.config import Configurator
from zope.interface import Interface, implementer

from kinto.core import utils


class IMetricsService(Interface):  # ty: ignore[unsupported-base]
    """
    An interface that defines the metrics service contract.
    Any class implementing this must provide all its methods.
    """

    def timer(key):
        """
        Watch execution time in seconds.
        """

    def observe(self, key, value, labels=[]):
        """
        Observe a give `value` for the specified `key`.
        """

    def count(key, count=1, unique=None):
        """
        Count occurrences. If `unique` is set, overwrites the counter value
        on each call.

        `unique` should be of type ``list[tuple[str,str]]``.
        """


class NoOpTimer:
    def __call__(self, f: Callable) -> Callable:
        @utils.safe_wraps(f)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        return _wrapped

    def __enter__(self) -> None:
        pass

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        pass


@implementer(IMetricsService)
class NoOpMetricsService:
    def timer(self, key: str, value: Any = None, labels: list = []) -> NoOpTimer:
        return NoOpTimer()

    def observe(self, key: str, value: Any, labels: list = []) -> None:
        pass

    def count(self, key: str, count: int = 1, unique: Any = None) -> None:
        pass


def watch_execution_time(
    metrics_service: Any, obj: Any, prefix: str = "", classname: str | None = None
) -> None:
    """
    Decorate all methods of an object in order to watch their execution time.
    Metrics will be named `{prefix}.{classname}.{method}`.
    """
    classname = classname or utils.classname(obj)
    members = dir(obj)
    for name in members:
        method = getattr(obj, name)
        is_method = isinstance(method, types.MethodType)
        if not name.startswith("_") and is_method:
            metric_name = f"{prefix}.{classname}.seconds"
            labels = [("method", name)]
            decorated_method = metrics_service.timer(metric_name, labels=labels)(method)
            setattr(obj, name, decorated_method)


def listener_with_timer(config: Configurator, key: str, func: Callable) -> Callable:
    """
    Add a timer with the specified `key` on the specified `func`.
    This is used to avoid evaluating `config.registry.metrics` during setup time
    to avoid having to deal with initialization order and configuration committing.
    """

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        metrics_service = config.registry.metrics  # ty: ignore[unresolved-attribute]
        if not metrics_service:
            # This only happens if `kinto.core.initialization.setup_metrics` is
            # not listed in the `initialization_sequence` setting.
            return func(*args, **kwargs)
        # If metrics are enabled, monitor execution time of listeners.
        with metrics_service.timer(key + ".seconds" if not key.endswith(".seconds") else key):
            return func(*args, **kwargs)

    return wrapped
