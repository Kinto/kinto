import logging
import random


logger = logging.getLogger(__name__)


_HEARTBEAT_DELETE_RATE = 0.5
_HEARTBEAT_KEY = "__heartbeat__"
_HEARTBEAT_TTL_SECONDS = 3600


class CacheBase:
    def __init__(self, *args, **kwargs):
        self.prefix = kwargs["cache_prefix"]
        self.max_size_bytes = kwargs.get("cache_max_size_bytes")

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
