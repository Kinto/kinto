import logging
from functools import wraps
from math import ceil, floor
from time import time

from pyramid.settings import aslist

from kinto.core.cache import CacheBase
from kinto.core.storage import exceptions
from kinto.core.utils import json, memcache

logger = logging.getLogger(__name__)


def wrap_memcached_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TypeError:
            raise
        except (
            memcache.Client.MemcachedKeyError,
            memcache.Client.MemcachedStringEncodingError,
        ) as e:
            logger.exception(e)
            raise exceptions.BackendError(original=e)

    return wrapped


def create_from_config(config, prefix=""):
    """Memcached client instantiation from settings.
    """
    settings = config.get_settings()
    hosts = aslist(settings[prefix + "hosts"])
    return memcache.Client(hosts)


class Cache(CacheBase):
    """Cache backend implementation using Memcached.

    Enable in configuration::

        kinto.cache_backend = kinto.core.cache.memcached

    *(Optional)* Instance location URI can be customized::

        kinto.cache_hosts = 127.0.0.1:11211 127.0.0.1:11212

    :noindex:

    """

    def __init__(self, client, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self._client = client

    def initialize_schema(self, dry_run=False):
        # Nothing to do.
        pass

    @wrap_memcached_error
    def flush(self):
        self._client.flush_all()

    @wrap_memcached_error
    def _get(self, key):
        value = self._client.get(self.prefix + key)
        if not value:
            return None, 0
        data = json.loads(value)
        return data["value"], data["ttl"]

    def ttl(self, key):
        _, ttl = self._get(key)
        val = ttl - time()
        return floor(val)

    def get(self, key):
        value, _ = self._get(key)
        return value

    @wrap_memcached_error
    def expire(self, key, ttl):
        if ttl == 0:
            self.delete(key)
        else:
            # We can't use touch here because we need to update the TTL value in the record.
            value = self.get(key)
            self.set(key, value, ttl)

    @wrap_memcached_error
    def set(self, key, value, ttl):
        if isinstance(value, bytes):
            raise TypeError("a string-like object is required, not 'bytes'")
        value = json.dumps({"value": value, "ttl": ceil(time() + ttl)})
        self._client.set(self.prefix + key, value, int(ttl))

    @wrap_memcached_error
    def delete(self, key):
        value = self.get(key)
        self._client.delete(self.prefix + key)
        return value


def load_from_config(config):
    settings = config.get_settings()
    client = create_from_config(config, prefix="cache_")
    return Cache(client, cache_prefix=settings["cache_prefix"])
