from __future__ import absolute_import
import time
import redis

from readinglist.session import SessionStorageBase


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

    def set(self, key, value):
        self._client.set(key, value)

    def get(self, key):
        value = self._client.get(key)
        if value:
            return value.decode('utf-8')

    def delete(self, key):
        self._client.delete(key)


def load_from_config(config):
    settings = config.registry.settings
    host = settings.get('session_redis.host', 'localhost')
    port = settings.get('session_redis.port', 6379)
    db = settings.get('session_redis.db', 1)
    return RedisSessionStorage(host=host, port=port, db=db)
