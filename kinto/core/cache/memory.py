from kinto.core import utils
from kinto.core.cache import CacheBase


class Cache(CacheBase):
    """Cache backend implementation in local thread memory.

    Enable in configuration::

        kinto.cache_backend = kinto.core.cache.memory

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
        ttl = self._ttl.get(self.prefix + key)
        if ttl is not None:
            return (ttl - utils.msec_time()) / 1000.0
        return -1

    def expire(self, key, ttl):
        self._ttl[self.prefix + key] = utils.msec_time() + int(ttl * 1000.0)

    def set(self, key, value, ttl=None):
        if ttl is not None:
            self.expire(key, ttl)
        self._store[self.prefix + key] = value

    def get(self, key):
        current = utils.msec_time()
        expired = [k for k, v in self._ttl.items() if current >= v]
        for expired_item_key in expired:
            self.delete(expired_item_key[len(self.prefix):])
        return self._store.get(self.prefix + key)

    def delete(self, key):
        key = self.prefix + key
        self._ttl.pop(key, None)
        self._store.pop(key, None)


def load_from_config(config):
    settings = config.get_settings()
    return Cache(cache_prefix=settings['cache_prefix'])
