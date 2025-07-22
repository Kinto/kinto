import logging
import random


logger = logging.getLogger(__name__)


_HEARTBEAT_DELETE_RATE = 0.5
_HEARTBEAT_KEY = "__heartbeat__"
_HEARTBEAT_TTL_SECONDS = 3600


_CACHE_HIT_METRIC_KEY = "cache_hits"
_CACHE_MISS_METRIC_KEY = "cache_misses"


class CacheBase:
    def __init__(self, *args, **kwargs):
        self.prefix = kwargs["cache_prefix"]
        self.max_size_bytes = kwargs.get("cache_max_size_bytes")
        self.set_metrics_backend(kwargs.get("metrics_backend"))

    def initialize_schema(self, dry_run=False):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is executed when the ``kinto migrate`` command is run.

        :param bool dry_run: simulate instead of executing the operations.
        """
        raise NotImplementedError

    def flush(self):
        """Delete every values."""
        raise NotImplementedError

    def ttl(self, key):
        """Obtain the expiration value of the specified `key`.

        :param str key: key
        :returns: number of seconds or negative if no TTL.
        :rtype: float
        """
        raise NotImplementedError

    def expire(self, key, ttl):
        """Set the expiration value `ttl` for the specified `key`.

        :param str key: key
        :param float ttl: number of seconds
        """
        raise NotImplementedError

    def set(self, key, value, ttl):
        """Store a value with the specified `key`.

        :param str key: key
        :param str value: value to store
        :param float ttl: expire after number of seconds
        """
        raise NotImplementedError

    def get(self, key):
        """Obtain the value of the specified `key`.

        :param str key: key
        :returns: the stored value or None if missing.
        :rtype: str
        """
        raise NotImplementedError

    def delete(self, key):
        """Delete the value of the specified `key`.

        :param str key: key
        """
        raise NotImplementedError

    def set_metrics_backend(self, metrics_backend):
        """Set metrics backend on the cache object.

        :param CacheMetricsBackend metrics_backend: Used to track cache-related metrics like hits and misses.
        """
        self.metrics_backend = metrics_backend


class CacheMetricsBackend:
    """
    A simple adapter for tracking cache-related metrics.
    """

    def __init__(self, metrics_backend):
        """Initialize with a given metrics backend.

        :param metrics_backend: A metrics backend implementing the IMetricsService interface.
        """
        self._backend = metrics_backend

    def count_hit(self):
        """Increment the cache hit counter."""
        self._backend.count(key=_CACHE_HIT_METRIC_KEY)

    def count_miss(self):
        """Increment the cache miss counter."""
        self._backend.count(key=_CACHE_MISS_METRIC_KEY)


def heartbeat(backend):
    def ping(request):
        """Test that cache backend is operational.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        # No specific case for readonly mode because the cache should
        # continue to work in that mode.
        try:
            if random.SystemRandom().random() < _HEARTBEAT_DELETE_RATE:
                backend.delete(_HEARTBEAT_KEY)
                return backend.get(_HEARTBEAT_KEY) is None
            backend.set(_HEARTBEAT_KEY, "alive", _HEARTBEAT_TTL_SECONDS)
            return backend.get(_HEARTBEAT_KEY) == "alive"
        except Exception:
            logger.exception("Heartbeat Failure")
            return False

    return ping
