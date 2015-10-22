from cliquet import utils
from cliquet.cache import CacheBase


class Cache(CacheBase):
    """Cache backend implementation in local thread memory.

    Enable in configuration::

        cliquet.cache_backend = cliquet.cache.memory

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self.flush()

    def initialize_schema(self):
        # Nothing to do.
        pass

    def flush(self):
        self._ttl = {}
        self._store = {}

    def ttl(self, key):
        ttl = self._ttl.get(key)
        if ttl is not None:
            return (ttl - utils.msec_time()) / 1000.0
        return -1

    def expire(self, key, ttl):
        self._ttl[key] = utils.msec_time() + int(ttl * 1000.0)

    def set(self, key, value, ttl=None):
        self._store[key] = value
        if ttl is not None:
            self.expire(key, ttl)

    def get(self, key):
        current = utils.msec_time()
        expired = [k for k, v in self._ttl.items() if current > v]
        for key in expired:
            self.delete(key)
        return self._store.get(key)

    def delete(self, key):
        self._ttl.pop(key, None)
        self._store.pop(key, None)


def load_from_config(config):
    return Cache()
