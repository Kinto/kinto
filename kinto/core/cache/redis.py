import logging
from functools import wraps
from urllib.parse import urlparse

from kinto.core.cache import CacheBase
from kinto.core.storage import exceptions
from kinto.core.utils import json, redis


logger = logging.getLogger(__name__)


def wrap_redis_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.exceptions.RedisError as e:
            logger.exception(e)
            raise exceptions.BackendError(original=e)

    return wrapped


class Cache(CacheBase):
    """Cache backend implementation using Redis.

    Enable in configuration::

        kinto.cache_backend = kinto.core.cache.memcached

    *(Optional)* Instance location URI can be customized::

        kinto.cache_url = redis://localhost:6379/1

    A threaded connection pool is enabled by default::

        kinto.cache_pool_size = 50
        kinto.cache_pool_timeout = 30

    If the database is used for multiple Kinto deployement cache, you
    may want to add a prefix to every key to avoid collision::

        kinto.cache_prefix = stack1_

    :noindex:

    """

    def __init__(self, client, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self._client = client

    @property
    def settings(self):
        return dict(self._client.connection_pool.connection_kwargs)

    def initialize_schema(self, dry_run=False):
        # Nothing to do.
        pass

    @wrap_redis_error
    def flush(self):
        self._client.flushdb()

    @wrap_redis_error
    def ttl(self, key):
        return self._client.ttl(self.prefix + key)

    @wrap_redis_error
    def expire(self, key, ttl):
        self._client.pexpire(self.prefix + key, int(ttl * 1000))

    @wrap_redis_error
    def set(self, key, value, ttl):
        if isinstance(value, bytes):
            raise TypeError("a string-like object is required, not 'bytes'")
        value = json.dumps(value)
        self._client.psetex(self.prefix + key, int(ttl * 1000), value)

    @wrap_redis_error
    def get(self, key):
        value = self._client.get(self.prefix + key)
        if value:
            self.metrics_backend.count_hit()
            value = value.decode("utf-8")
            return json.loads(value)
        self.metrics_backend.count_miss()

    @wrap_redis_error
    def delete(self, key):
        value = self.get(key)
        self._client.delete(self.prefix + key)
        return value


def create_from_config(config, prefix=""):
    """Redis client instantiation from settings."""
    settings = config.get_settings()
    uri = settings[prefix + "url"]
    uri = urlparse(uri)
    kwargs = {
        "host": uri.hostname or "localhost",
        "port": uri.port or 6379,
        "password": uri.password or None,
        "db": int(uri.path[1:]) if uri.path else 0,
    }

    pool_size = settings.get(prefix + "pool_size")
    if pool_size is not None:
        kwargs["max_connections"] = int(pool_size)

    block_timeout = settings.get(prefix + "pool_timeout")
    if block_timeout is not None:
        kwargs["timeout"] = float(block_timeout)

    connection_pool = redis.BlockingConnectionPool(**kwargs)
    return redis.StrictRedis(connection_pool=connection_pool)


def load_from_config(config):
    settings = config.get_settings()
    client = create_from_config(config, prefix="cache_")
    return Cache(client, cache_prefix=settings["cache_prefix"])
