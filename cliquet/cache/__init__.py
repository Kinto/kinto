import random


_HEARTBEAT_DELETE_RATE = 0.5
_HEARTBEAT_KEY = '__heartbeat__'
_HEARTBEAT_TTL_SECONDS = 3600


class CacheBase(object):

    def __init__(self, *args, **kwargs):
        pass

    def initialize_schema(self):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is excuted when the ``cliquet migrate`` command is ran.
        """
        raise NotImplementedError

    def flush(self):
        """Delete every values."""
        raise NotImplementedError

    def ping(self, request):
        """Test that cache backend is operationnal.

        :param request: current request object
        :type request: :class:`~pyramid:pyramid.request.Request`
        :returns: ``True`` is everything is ok, ``False`` otherwise.
        :rtype: bool
        """
        try:
            if random.random() < _HEARTBEAT_DELETE_RATE:
                self.delete(_HEARTBEAT_KEY)
            else:
                self.set(_HEARTBEAT_KEY, 'alive', _HEARTBEAT_TTL_SECONDS)
            return True
        except:
            return False

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

    def set(self, key, value, ttl=None):
        """Store a value with the specified `key`. If `ttl` is provided,
        set an expiration value.

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
