import logging

from kinto.core.cache import CacheBase
from kinto.core.utils import msec_time
from kinto.core.decorators import synchronized


logger = logging.getLogger(__name__)


class Cache(CacheBase):
    """Cache backend implementation in local process memory.

    Enable in configuration::

        kinto.cache_backend = kinto.core.cache.memory

    :noindex:
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flush()

    def initialize_schema(self, dry_run=False):
        # Nothing to do.
        pass

    def flush(self):
        self._created_at = {}
        self._ttl = {}
        self._store = {}
        self._quota = 0

    def _clean_expired(self):
        current = msec_time()
        expired = [k for k, v in self._ttl.items() if current >= v]
        for expired_item_key in expired:
            self.delete(expired_item_key[len(self.prefix):])

    def _clean_oversized(self):
        if self._quota < self.max_size_bytes:
            return

        for key, value in sorted(self._created_at.items(), key=lambda k: k[1]):
            if self._quota < (self.max_size_bytes * 0.8):
                break
            self.delete(key[len(self.prefix):])

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
    def set(self, key, value, ttl):
        if isinstance(value, bytes):
            raise TypeError("a string-like object is required, not 'bytes'")
        self._clean_expired()
        self._clean_oversized()
        self.expire(key, ttl)
        item_key = self.prefix + key
        self._store[item_key] = value
        self._created_at[item_key] = msec_time()
        self._quota += size_of(item_key, value)

    @synchronized
    def get(self, key):
        self._clean_expired()
        return self._store.get(self.prefix + key)

    @synchronized
    def delete(self, key):
        key = self.prefix + key
        self._ttl.pop(key, None)
        self._created_at.pop(key, None)
        value = self._store.pop(key, None)
        self._quota -= size_of(key, value)
        return value


def load_from_config(config):
    settings = config.get_settings()
    return Cache(cache_prefix=settings['cache_prefix'],
                 cache_max_size_bytes=settings['cache_max_size_bytes'])


def size_of(key, value):
    # Key used for ttl, created_at and store.
    # Int size is 24 bytes one for ttl and one for created_at values
    return len(key) * 3 + len(str(value)) + 24 * 2
