from __future__ import absolute_import, unicode_literals
from functools import wraps

import redis
from six.moves.urllib import parse as urlparse

from cliquet import utils, logger
from cliquet.storage import (
    exceptions, DEFAULT_ID_FIELD,
    DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD)
from cliquet.storage.memory import MemoryBasedStorage


def wrap_redis_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.RedisError as e:
            logger.exception(e)
            raise exceptions.BackendError(original=e)
    return wrapped


def create_from_config(config, prefix=''):
    """Redis client instantiation from settings.
    """
    settings = config.get_settings()
    uri = settings[prefix + 'url']
    uri = urlparse.urlparse(uri)
    pool_size = int(settings[prefix + 'pool_size'])
    kwargs = {
        "max_connections": pool_size,
        "host": uri.hostname or 'localhost',
        "port": uri.port or 6379,
        "password": uri.password or None,
        "db": int(uri.path[1:]) if uri.path else 0
    }
    connection_pool = redis.BlockingConnectionPool(**kwargs)
    return redis.StrictRedis(connection_pool=connection_pool)


class Storage(MemoryBasedStorage):
    """Storage backend implementation using Redis.

    .. warning::

        Useful for very low server load, but won't scale since records sorting
        and filtering are performed in memory.

    Enable in configuration::

        cliquet.storage_backend = cliquet.storage.redis

    *(Optional)* Instance location URI can be customized::

        cliquet.storage_url = redis://localhost:6379/0

    A threaded connection pool is enabled by default::

        cliquet.storage_pool_size = 50
    """

    def __init__(self, client, *args, **kwargs):
        super(Storage, self).__init__(*args, **kwargs)
        self._client = client

    @property
    def settings(self):
        return dict(self._client.connection_pool.connection_kwargs)

    def _encode(self, record):
        return utils.json.dumps(record)

    def _decode(self, record):
        return utils.json.loads(record.decode('utf-8'))

    @wrap_redis_error
    def flush(self, auth=None):
        self._client.flushdb()

    @wrap_redis_error
    def collection_timestamp(self, collection_id, parent_id, auth=None):
        timestamp = self._client.get(
            '{0}.{1}.timestamp'.format(collection_id, parent_id))
        if timestamp:
            return int(timestamp)
        return self._bump_timestamp(collection_id, parent_id)

    @wrap_redis_error
    def _bump_timestamp(self, collection_id, parent_id, record=None,
                        modified_field=None, last_modified=None):

        key = '{0}.{1}.timestamp'.format(collection_id, parent_id)
        while 1:
            with self._client.pipeline() as pipe:
                try:
                    pipe.watch(key)
                    previous = pipe.get(key)
                    pipe.multi()
                    # XXX factorize code from memory and redis backends.
                    is_specified = (record is not None and
                                    modified_field in record or
                                    last_modified is not None)
                    if is_specified:
                        # If there is a timestamp in the new record,
                        # try to use it.
                        if last_modified is not None:
                            current = last_modified
                        else:
                            current = record[modified_field]
                    else:
                        current = utils.msec_time()

                    if previous and int(previous) >= current:
                        collection_timestamp = int(previous) + 1
                    else:
                        collection_timestamp = current

                    # Return the newly generated timestamp as the current one
                    # only if nothing else was specified.
                    if not is_specified:
                        current = collection_timestamp

                    pipe.set(key, collection_timestamp)
                    pipe.execute()
                    return current
                except redis.WatchError:  # pragma: no cover
                    # Our timestamp has been modified by someone else, let's
                    # retry.
                    # XXX: untested.
                    continue

    @wrap_redis_error
    def create(self, collection_id, parent_id, record, id_generator=None,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        self.check_unicity(collection_id, parent_id, record,
                           unique_fields=unique_fields, id_field=id_field,
                           for_creation=True)

        record = record.copy()
        id_generator = id_generator or self.id_generator
        _id = record.setdefault(id_field, id_generator())
        self.set_record_timestamp(collection_id, parent_id, record,
                                  modified_field=modified_field)

        record_key = '{0}.{1}.{2}.records'.format(collection_id,
                                                  parent_id,
                                                  _id)
        with self._client.pipeline() as multi:
            multi.set(
                record_key,
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}.records'.format(collection_id, parent_id),
                _id
            )
            multi.srem(
                '{0}.{1}.deleted'.format(collection_id, parent_id),
                _id
            )
            multi.execute()

        return record

    @wrap_redis_error
    def get(self, collection_id, parent_id, object_id,
            id_field=DEFAULT_ID_FIELD,
            modified_field=DEFAULT_MODIFIED_FIELD,
            auth=None):
        record_key = '{0}.{1}.{2}.records'.format(collection_id,
                                                  parent_id,
                                                  object_id)
        encoded_item = self._client.get(record_key)
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(object_id)

        return self._decode(encoded_item)

    @wrap_redis_error
    def update(self, collection_id, parent_id, object_id, record,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        record = record.copy()
        record[id_field] = object_id
        self.check_unicity(collection_id, parent_id, record,
                           unique_fields=unique_fields, id_field=id_field)

        self.set_record_timestamp(collection_id, parent_id, record,
                                  modified_field=modified_field)

        record_key = '{0}.{1}.{2}.records'.format(collection_id,
                                                  parent_id,
                                                  object_id)
        with self._client.pipeline() as multi:
            multi.set(
                record_key,
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}.records'.format(collection_id, parent_id),
                object_id
            )
            multi.execute()

        return record

    @wrap_redis_error
    def delete(self, collection_id, parent_id, object_id,
               id_field=DEFAULT_ID_FIELD, with_deleted=True,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None, last_modified=None):
        record_key = '{0}.{1}.{2}.records'.format(collection_id,
                                                  parent_id,
                                                  object_id)
        with self._client.pipeline() as multi:
            multi.get(record_key)
            multi.delete(record_key)
            multi.srem(
                '{0}.{1}.records'.format(collection_id, parent_id),
                object_id
            )
            responses = multi.execute()

        encoded_item = responses[0]
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(object_id)

        existing = self._decode(encoded_item)

        # Need to delete the last_modified field.
        del existing[modified_field]

        self.set_record_timestamp(collection_id, parent_id, existing,
                                  modified_field=modified_field,
                                  last_modified=last_modified)
        existing = self.strip_deleted_record(collection_id, parent_id,
                                             existing)

        if with_deleted:
            deleted_record_key = '{0}.{1}.{2}.deleted'.format(collection_id,
                                                              parent_id,
                                                              object_id)
            with self._client.pipeline() as multi:
                multi.set(
                    deleted_record_key,
                    self._encode(existing)
                )
                multi.sadd(
                    '{0}.{1}.deleted'.format(collection_id, parent_id),
                    object_id
                )
                multi.execute()

        return existing

    @wrap_redis_error
    def purge_deleted(self, collection_id, parent_id, before=None,
                      id_field=DEFAULT_ID_FIELD,
                      modified_field=DEFAULT_MODIFIED_FIELD,
                      auth=None):
        deleted_ids = '{0}.{1}.deleted'.format(collection_id, parent_id)
        ids = self._client.smembers(deleted_ids)

        keys = ['{0}.{1}.{2}.deleted'.format(collection_id, parent_id,
                                             _id.decode('utf-8'))
                for _id in ids]

        if len(keys) == 0:
            deleted = []
        else:
            encoded_results = self._client.mget(keys)
            deleted = [self._decode(r) for r in encoded_results if r]
        if before is not None:
            to_remove = [d['id'] for d in deleted
                         if d[modified_field] < before]
        else:
            to_remove = [d['id'] for d in deleted]

        if len(to_remove) > 0:
            with self._client.pipeline() as pipe:
                pipe.delete(*['{0}.{1}.{2}.deleted'.format(
                    collection_id, parent_id, _id) for _id in to_remove])
                pipe.srem(deleted_ids, *to_remove)
                pipe.execute()
        number_deleted = len(to_remove)
        return number_deleted

    @wrap_redis_error
    def get_all(self, collection_id, parent_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False,
                id_field=DEFAULT_ID_FIELD,
                modified_field=DEFAULT_MODIFIED_FIELD,
                deleted_field=DEFAULT_DELETED_FIELD,
                auth=None):
        records_ids_key = '{0}.{1}.records'.format(collection_id, parent_id)
        ids = self._client.smembers(records_ids_key)

        keys = ('{0}.{1}.{2}.records'.format(collection_id, parent_id,
                                             _id.decode('utf-8'))
                for _id in ids)

        if len(ids) == 0:
            records = []
        else:
            encoded_results = self._client.mget(keys)
            records = [self._decode(r) for r in encoded_results if r]

        deleted = []
        if include_deleted:
            deleted_ids = '{0}.{1}.deleted'.format(collection_id, parent_id)
            ids = self._client.smembers(deleted_ids)

            keys = ['{0}.{1}.{2}.deleted'.format(collection_id, parent_id,
                                                 _id.decode('utf-8'))
                    for _id in ids]

            if len(keys) == 0:
                deleted = []
            else:
                encoded_results = self._client.mget(keys)
                deleted = [self._decode(r) for r in encoded_results if r]

        records, count = self.extract_record_set(collection_id,
                                                 records + deleted,
                                                 filters, sorting,
                                                 id_field, deleted_field,
                                                 pagination_rules, limit)

        return records, count


def load_from_config(config):
    client = create_from_config(config, prefix='storage_')
    return Storage(client)
