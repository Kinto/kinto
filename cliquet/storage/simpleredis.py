import json
import redis
import time

from cliquet.storage import (
    StorageBase, exceptions, extract_record_set
)

from cliquet import utils
from cliquet.utils import classname


class Redis(StorageBase):

    def __init__(self, *args, **kwargs):
        super(Redis, self).__init__(*args, **kwargs)
        self._client = redis.StrictRedis(
            connection_pool=redis.BlockingConnectionPool(),
            **kwargs
        )

    def _encode(self, record):
        return json.dumps(record)

    def _decode(self, record):
        if record is None:
            return record
        return json.loads(record.decode('utf-8'))

    def flush(self):
        self._client.flushdb()

    def ping(self):
        try:
            self._client.setex('heartbeat', 3600, time.time())
            return True
        except redis.RedisError:
            return False

    def collection_timestamp(self, resource, user_id):
        """Return the last timestamp for the resource collection of the user"""
        resource_name = classname(resource)
        timestamp = self._client.get(
            '{0}.{1}.timestamp'.format(resource_name, user_id))
        if timestamp:
            return int(timestamp)
        return utils.msec_time()

    def _bump_timestamp(self, resource, user_id):
        resource_name = classname(resource)
        key = '{0}.{1}.timestamp'.format(resource_name, user_id)
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

    def create(self, resource, user_id, record):
        self.check_unicity(resource, user_id, record)

        record = record.copy()
        _id = record[resource.id_field] = self.id_generator()
        self.set_record_timestamp(resource, user_id, record)

        resource_name = classname(resource)
        record_key = '{0}.{1}.{2}.records'.format(resource_name,
                                                  user_id,
                                                  _id)
        with self._client.pipeline() as multi:
            multi.set(
                record_key,
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}.records'.format(resource_name, user_id),
                _id
            )
            multi.execute()

        return record

    def get(self, resource, user_id, record_id):
        resource_name = classname(resource)
        record_key = '{0}.{1}.{2}.records'.format(resource_name,
                                                  user_id,
                                                  record_id)
        encoded_item = self._client.get(record_key)
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(record_id)

        return self._decode(encoded_item)

    def update(self, resource, user_id, record_id, record):
        record = record.copy()
        record[resource.id_field] = record_id
        self.check_unicity(resource, user_id, record)

        self.set_record_timestamp(resource, user_id, record)

        resource_name = classname(resource)
        record_key = '{0}.{1}.{2}.records'.format(resource_name,
                                                  user_id,
                                                  record_id)
        with self._client.pipeline() as multi:
            multi.set(
                record_key,
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}.records'.format(resource_name, user_id),
                record_id
            )
            multi.execute()

        return record

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        record_key = '{0}.{1}.{2}.records'.format(resource_name,
                                                  user_id,
                                                  record_id)
        with self._client.pipeline() as multi:
            multi.get(record_key)
            multi.delete(record_key)
            multi.srem(
                '{0}.{1}.records'.format(resource_name, user_id),
                record_id
            )
            responses = multi.execute()

        encoded_item = responses[0]
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(record_id)

        existing = self._decode(encoded_item)
        self.set_record_timestamp(resource, user_id, existing)
        existing = self.strip_deleted_record(resource, user_id, existing)

        deleted_record_key = '{0}.{1}.{2}.deleted'.format(resource_name,
                                                          user_id,
                                                          record_id)
        with self._client.pipeline() as multi:
            multi.set(
                deleted_record_key,
                self._encode(existing)
            )
            multi.sadd(
                '{0}.{1}.deleted'.format(resource_name, user_id),
                record_id
            )
            multi.execute()

        return existing

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        resource_name = classname(resource)
        records_ids_key = '{0}.{1}.records'.format(resource_name, user_id)
        ids = self._client.smembers(records_ids_key)

        keys = ('{0}.{1}.{2}.records'.format(resource_name, user_id,
                                             _id.decode('utf-8'))
                for _id in ids)

        if len(ids) == 0:
            records = []
        else:
            encoded_results = self._client.mget(keys)
            records = [self._decode(r) for r in encoded_results if r]

        deleted = {}
        if include_deleted:
            deleted_ids_key = '{0}.{1}.deleted'.format(resource_name, user_id)
            ids = self._client.smembers(deleted_ids_key)

            keys = ('{0}.{1}.{2}.deleted'.format(resource_name, user_id,
                                                 _id.decode('utf-8'))
                    for _id in ids)

            encoded_results = self._client.mget(keys)
            results = [self._decode(r) for r in encoded_results if r]
            for result in results:
                deleted[result[resource.id_field]] = result

        records, count = extract_record_set(resource,
                                            records + list(deleted.values()),
                                            filters, sorting,
                                            pagination_rules, limit)

        filtered_deleted = len([r for r in records
                                if r[resource.id_field] in deleted])

        return records, count - filtered_deleted


def load_from_config(config):
    settings = config.registry.settings
    host = settings.get('redis.host', 'localhost')
    port = settings.get('redis.port', 6379)
    db = settings.get('redis.db', 0)
    return Redis(host=host, port=port, db=db)
