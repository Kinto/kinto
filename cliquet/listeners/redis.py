from __future__ import absolute_import
from six.moves.urllib import parse as urlparse
import redis
import json

from cliquet.listeners import ListenerBase
from cliquet import logger


class RedisListener(ListenerBase):
    def __init__(self, *args, **kwargs):
        super(RedisListener, self).__init__(*args, **kwargs)
        self.listname = kwargs.pop('listname')
        connection_pool = redis.BlockingConnectionPool(**kwargs)
        self._client = redis.StrictRedis(connection_pool=connection_pool)

    def __call__(self, event):
        try:
            payload = json.dumps(event.payload)
        except TypeError:
            logger.error("Unable to dump the payload", exc_info=True)
            return

        try:
            self._client.lpush(self.listname, payload)
        except Exception:
            logger.error("Unable to send the payload to Redis", exc_info=True)


def _get_options(config, prefix='event_listeners.redis.'):
    options = {}

    for name, value in config.get_settings().items():
        if not name.startswith(prefix):
            continue
        options[name[len(prefix):]] = value

    return options


def load_from_config(config):
    options = _get_options(config)

    uri = options.get('url', 'http://localhost:6379')
    uri = urlparse.urlparse(uri)
    pool_size = int(options.get('pool_size', 1))
    listname = options.get('listname', 'cliquet.events')

    return RedisListener(listname=listname,
                         max_connections=pool_size,
                         host=uri.hostname or 'localhost',
                         port=uri.port or 6379,
                         password=uri.password or None,
                         db=int(uri.path[1:]) if uri.path else 0)
