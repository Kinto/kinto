from kinto.core.cache import CacheBase
from kinto.core.utils import msec_time, synchronized


class Cache(CacheBase):
    """Cache backend implementation in local process memory.

    Enable in configuration::

        kinto.cache_backend = kinto.core.cache.memory

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self.flush()

    def initialize_schema(self, dry_run=False):
        # Nothing to do.
        pass

    def flush(self):
        self._ttl = {}
        self._store = {}

    @synchronized
    def ttl(self, key):
        ttl = self._ttl.get(self.prefix + key)
        if ttl is not None:
            return (ttl - msec_time()) / 1000.0
        return -1

    @synchronized
    def expire(self, key, ttl):
        self._ttl[self.prefix + key] = msec_time() + int(ttl * 1000.0)

    @synchronized
    def set(self, key, value, ttl=None):
        if ttl is not None:
            self.expire(key, ttl)
        self._store[self.prefix + key] = value

    @synchronized
    def get(self, key):
        current = msec_time()
        expired = [k for k, v in self._ttl.items() if current >= v]
        for expired_item_key in expired:
            self.delete(expired_item_key[len(self.prefix):])
        return self._store.get(self.prefix + key)

    @synchronized
    def delete(self, key):
        key = self.prefix + key
        self._ttl.pop(key, None)
        self._store.pop(key, None)


def load_from_config(config):
    settings = config.get_settings()
    return Cache(cache_prefix=settings['cache_prefix'])
