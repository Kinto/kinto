from __future__ import absolute_import
from functools import wraps

import redis
import time
from six.moves.urllib import parse as urlparse

from cliquet import utils
from cliquet.storage import exceptions
from cliquet.storage.memory import MemoryBasedStorage


def wrap_redis_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.RedisError as e:
            raise exceptions.BackendError(original=e)
    return wrapped


class Redis(MemoryBasedStorage):
    """Storage backend implementation using Redis.

    :warning:
        Useful for very low server load, but won't scale since records sorting
        and filtering are performed in memory.

    Enable in configuration::

        cliquet.storage_backend = cliquet.storage.redis

    *(Optional)* Instance location URI can be customized::

        cliquet.storage_url = redis://localhost:6379/0

    A threaded connection pool is enabled by default::

        cliquet.storage_pool_maxconn = 50
    """

    def __init__(self, *args, **kwargs):
        super(Redis, self).__init__(*args, **kwargs)
        kwargs.pop('id_generator', None)
        maxconn = kwargs.pop('max_connections')
        connection_pool = redis.BlockingConnectionPool(max_connections=maxconn)
        self._client = redis.StrictRedis(connection_pool=connection_pool,
                                         **kwargs)

    def _encode(self, record):
        return utils.json.dumps(record)

    def _decode(self, record):
        if record is None:
            return record
        return utils.json.loads(record.decode('utf-8'))

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
    def collection_timestamp(self, resource, user_id):
        timestamp = self._client.get(
            '{0}.{1}.timestamp'.format(resource.name, user_id))
        if timestamp:
            return int(timestamp)
        return self._bump_timestamp(resource, user_id)

    @wrap_redis_error
    def _bump_timestamp(self, resource, user_id):
        key = '{0}.{1}.timestamp'.format(resource.name, user_id)
        while 1:
            with self._client.pipeline() as pipe:
                try:
                    pipe.watch(key)
                    previous = pipe.get(key)
                    pipe.multi()
                    current = utils.msec_time()

                    if previous and int(previous) >= current:
                        current = int(previous) + 1
                    pipe.set(key, current)
                    pipe.execute()
                    return current
                except redis.WatchError:
                    # Our timestamp has been modified by someone else, let's
                    # retry
                    continue

    @wrap_redis_error
    def create(self, resource, user_id, record):
        self.check_unicity(resource, user_id, record)

        record = record.copy()
        _id = record[resource.id_field] = self.id_generator()
        self.set_record_timestamp(resource, user_id, record)

        record_key = '{0}.{1}.{2}.records'.format(resource.name,
                                                  user_id,
                                                  _id)
        with self._client.pipeline() as multi:
            multi.set(
                record_key,
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}.records'.format(resource.name, user_id),
                _id
            )
            multi.execute()

        return record

    @wrap_redis_error
    def get(self, resource, user_id, record_id):
        record_key = '{0}.{1}.{2}.records'.format(resource.name,
                                                  user_id,
                                                  record_id)
        encoded_item = self._client.get(record_key)
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(record_id)

        return self._decode(encoded_item)

    @wrap_redis_error
    def update(self, resource, user_id, record_id, record):
        record = record.copy()
        record[resource.id_field] = record_id
        self.check_unicity(resource, user_id, record)

        self.set_record_timestamp(resource, user_id, record)

        record_key = '{0}.{1}.{2}.records'.format(resource.name,
                                                  user_id,
                                                  record_id)
        with self._client.pipeline() as multi:
            multi.set(
                record_key,
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}.records'.format(resource.name, user_id),
                record_id
            )
            multi.execute()

        return record

    @wrap_redis_error
    def delete(self, resource, user_id, record_id):
        record_key = '{0}.{1}.{2}.records'.format(resource.name,
                                                  user_id,
                                                  record_id)
        with self._client.pipeline() as multi:
            multi.get(record_key)
            multi.delete(record_key)
            multi.srem(
                '{0}.{1}.records'.format(resource.name, user_id),
                record_id
            )
            responses = multi.execute()

        encoded_item = responses[0]
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(record_id)

        existing = self._decode(encoded_item)
        self.set_record_timestamp(resource, user_id, existing)
        existing = self.strip_deleted_record(resource, user_id, existing)

        deleted_record_key = '{0}.{1}.{2}.deleted'.format(resource.name,
                                                          user_id,
                                                          record_id)
        with self._client.pipeline() as multi:
            multi.set(
                deleted_record_key,
                self._encode(existing)
            )
            multi.sadd(
                '{0}.{1}.deleted'.format(resource.name, user_id),
                record_id
            )
            multi.execute()

        return existing

    @wrap_redis_error
    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        records_ids_key = '{0}.{1}.records'.format(resource.name, user_id)
        ids = self._client.smembers(records_ids_key)

        keys = ('{0}.{1}.{2}.records'.format(resource.name, user_id,
                                             _id.decode('utf-8'))
                for _id in ids)

        if len(ids) == 0:
            records = []
        else:
            encoded_results = self._client.mget(keys)
            records = [self._decode(r) for r in encoded_results if r]

        deleted = []
        if include_deleted:
            deleted_ids_key = '{0}.{1}.deleted'.format(resource.name, user_id)
            ids = self._client.smembers(deleted_ids_key)

            keys = ['{0}.{1}.{2}.deleted'.format(resource.name, user_id,
                                                 _id.decode('utf-8'))
                    for _id in ids]

            if len(keys) == 0:
                deleted = []
            else:
                encoded_results = self._client.mget(keys)
                deleted = [self._decode(r) for r in encoded_results if r]

        records, count = self.extract_record_set(resource,
                                                 records + deleted,
                                                 filters, sorting,
                                                 pagination_rules, limit)

        return records, count


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['cliquet.storage_url']
    uri = urlparse.urlparse(uri)
    pool_maxconn = int(settings['cliquet.storage_pool_maxconn'])

    return Redis(max_connections=pool_maxconn,
                 host=uri.hostname or 'localhost',
                 port=uri.port or 6739,
                 password=uri.password or None,
                 db=int(uri.path[1:]) if uri.path else 0)
