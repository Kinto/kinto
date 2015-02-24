from __future__ import absolute_import
import time

import redis
from six.moves.urllib import parse as urlparse

from cliquet.session import SessionStorageBase


class RedisSessionStorage(SessionStorageBase):
    def __init__(self, *args, **kwargs):
        super(RedisSessionStorage, self).__init__(*args, **kwargs)
        self._client = redis.StrictRedis(
            connection_pool=redis.BlockingConnectionPool(),
            **kwargs
        )

    def flush(self):
        self._client.flushdb()

    def ping(self):
        try:
            self._client.setex('heartbeat', 3600, time.time())
            return True
        except redis.RedisError:
            return False

    def ttl(self, key):
        return self._client.ttl(key)

    def expire(self, key, value):
        self._client.pexpire(key, int(value * 1000))

    def set(self, key, value, ttl=None):
        if ttl:
            self._client.psetex(key, int(ttl * 1000), value)
        else:
            self._client.set(key, value)

    def get(self, key):
        value = self._client.get(key)
        if value:
            return value.decode('utf-8')

    def delete(self, key):
        self._client.delete(key)


def load_from_config(config):
    settings = config.registry.settings
    uri = settings.get('cliquet.session_url', '')
    uri = urlparse.urlparse(uri)

    return RedisSessionStorage(host=uri.hostname or 'localhost',
                               port=uri.port or 6739,
                               password=uri.password or None,
                               db=int(uri.path[1:]) if uri.path else 0)
