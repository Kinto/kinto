from __future__ import absolute_import

from cliquet.cache import CacheBase
from cliquet.storage.redis import wrap_redis_error, create_from_config
from cliquet.utils import json


class Cache(CacheBase):
    """Cache backend implementation using Redis.

    Enable in configuration::

        cliquet.cache_backend = cliquet.cache.redis

    *(Optional)* Instance location URI can be customized::

        cliquet.cache_url = redis://localhost:6379/1

    A threaded connection pool is enabled by default::

        cliquet.cache_pool_size = 50

    :noindex:
    """

    def __init__(self, client, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self._client = client

    @property
    def settings(self):
        return dict(self._client.connection_pool.connection_kwargs)

    def initialize_schema(self):
        # Nothing to do.
        pass

    @wrap_redis_error
    def flush(self):
        self._client.flushdb()

    @wrap_redis_error
    def ttl(self, key):
        return self._client.ttl(key)

    @wrap_redis_error
    def expire(self, key, ttl):
        self._client.pexpire(key, int(ttl * 1000))

    @wrap_redis_error
    def set(self, key, value, ttl=None):
        value = json.dumps(value)
        if ttl:
            self._client.psetex(key, int(ttl * 1000), value)
        else:
            self._client.set(key, value)

    @wrap_redis_error
    def get(self, key):
        value = self._client.get(key)
        if value:
            value = value.decode('utf-8')
            return json.loads(value)

    @wrap_redis_error
    def delete(self, key):
        self._client.delete(key)


def load_from_config(config):
    client = create_from_config(config, prefix='cache_')
    return Cache(client)
