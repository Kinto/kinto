from __future__ import absolute_import
import time

import redis
from six.moves.urllib import parse as urlparse

from cliquet.cache import CacheBase
from cliquet.storage.redis import wrap_redis_error


class Redis(CacheBase):
    """Cache backend implementation using Redis.

    Enable in configuration::

        cliquet.cache_backend = cliquet.cache.redis

    *(Optional)* Instance location URI can be customized::

        cliquet.cache_url = redis://localhost:6379/1

    A threaded connection pool is enabled by default::

        cliquet.cache_pool_maxconn = 50
    """

    def __init__(self, *args, **kwargs):
        super(Redis, self).__init__(*args, **kwargs)
        maxconn = kwargs.pop('max_connections')
        connection_pool = redis.BlockingConnectionPool(max_connections=maxconn)
        self._client = redis.StrictRedis(connection_pool=connection_pool,
                                         **kwargs)

    @wrap_redis_error
    def flush(self):
        self._client.flushdb()

    def ping(self):
        try:
            self._client.setex('heartbeat', 3600, time.time())
            return True
        except redis.RedisError:
            return False

    @wrap_redis_error
    def ttl(self, key):
        return self._client.ttl(key)

    @wrap_redis_error
    def expire(self, key, value):
        self._client.pexpire(key, int(value * 1000))

    @wrap_redis_error
    def set(self, key, value, ttl=None):
        if ttl:
            self._client.psetex(key, int(ttl * 1000), value)
        else:
            self._client.set(key, value)

    @wrap_redis_error
    def get(self, key):
        value = self._client.get(key)
        if value:
            return value.decode('utf-8')

    @wrap_redis_error
    def delete(self, key):
        self._client.delete(key)


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['cliquet.cache_url']
    uri = urlparse.urlparse(uri)
    pool_maxconn = int(settings['cliquet.cache_pool_maxconn'])

    return Redis(max_connections=pool_maxconn,
                 host=uri.hostname or 'localhost',
                 port=uri.port or 6739,
                 password=uri.password or None,
                 db=int(uri.path[1:]) if uri.path else 0)
