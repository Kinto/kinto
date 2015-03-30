class CacheBase(object):

    def __init__(self, *args, **kwargs):
        pass

    def initialize_schema(self):
        """Create every necessary objects (like tables or indices) in the
        backend.

        This is excuted when the ``cliquet init`` command is ran.
        """
        raise NotImplementedError

    def flush(self):
        """Delete every values."""
        raise NotImplementedError

    def ping(self):
        """Test that cache backend is operationnal.

        :returns: `True` is everything is ok, `False` otherwise.
        :rtype: boolean
        """
        raise NotImplementedError

    def ttl(self, key):
        """Obtain the expiration value of the specified key.

        :param key: key
        :type key: string
        :returns: number of seconds or negative if no TTL.
        :rtype: float
        """
        raise NotImplementedError

    def expire(self, key, ttl):
        """Set the expiration value of the specified key.

        :param key: key
        :type key: string
        :param ttl: number of seconds
        :type ttl: float
        """
        raise NotImplementedError

    def set(self, key, value, ttl=None):
        """Store a value with the specified key.

        :param key: key
        :type key: string
        :param value: value to store
        :type value: string
        :param ttl: expire after number of seconds
        :type ttl: float
        """
        raise NotImplementedError

    def get(self, key):
        """Obtain the value of the specified key.

        :param key: key
        :type key: string
        :returns: the stored value or None if missing.
        :rtype: string
        """
        raise NotImplementedError

    def delete(self, key):
        """Delete the value of the specified key.

        :param key: key
        :type key: string
        """
        raise NotImplementedError
