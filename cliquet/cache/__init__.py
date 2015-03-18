class CacheBase(object):
    def __init__(self, *args, **kwargs):
        pass

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


class SessionCache(object):
    def __init__(self, cache, ttl):
        self.cache = cache
        self.ttl = ttl

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache.set(key, value, self.ttl)

    def delete(self, key):
        self.cache.delete(key)
