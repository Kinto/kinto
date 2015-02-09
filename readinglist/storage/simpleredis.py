import json
import redis
import time

from readinglist.storage import (
    StorageBase, exceptions, extract_record_set
)

from readinglist import utils
from readinglist.utils import classname


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
        with self._client.pipeline() as multi:
            multi.set(
                '{0}.{1}.{2}'.format(resource_name, user_id, _id),
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}'.format(resource_name, user_id),
                _id
            )
            multi.execute()

        return record

    def get(self, resource, user_id, record_id):
        resource_name = classname(resource)

        encoded_item = self._client.get(
            '{0}.{1}.{2}'.format(resource_name, user_id, record_id)
        )
        if encoded_item is None:
            raise exceptions.RecordNotFoundError(record_id)

        return self._decode(encoded_item)

    def update(self, resource, user_id, record_id, record):
        record = record.copy()
        record[resource.id_field] = record_id
        self.check_unicity(resource, user_id, record)

        self.set_record_timestamp(resource, user_id, record)

        resource_name = classname(resource)
        with self._client.pipeline() as multi:
            multi.set(
                '{0}.{1}.{2}'.format(resource_name, user_id, record_id),
                self._encode(record)
            )
            multi.sadd(
                '{0}.{1}'.format(resource_name, user_id),
                record_id
            )
            multi.execute()

        return record

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        with self._client.pipeline() as multi:
            multi.get(
                '{0}.{1}.{2}'.format(resource_name, user_id, record_id)
            )
            multi.delete(
                '{0}.{1}.{2}'.format(resource_name, user_id, record_id))

            multi.srem(
                '{0}.{1}'.format(resource_name, user_id),
                record_id
            )
            responses = multi.execute()
            encoded_item = responses[0]

            if encoded_item is None:
                raise exceptions.RecordNotFoundError(record_id)

            self._bump_timestamp(resource, user_id)
            return self._decode(encoded_item)

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None):
        resource_name = classname(resource)
        ids = self._client.smembers('{0}.{1}'.format(resource_name, user_id))

        if (len(ids) == 0):
            return [], 0

        keys = ('{0}.{1}.{2}'.format(resource_name, user_id,
                                     _id.decode('utf-8'))
                for _id in ids)

        encoded_results = self._client.mget(keys)
        records = map(self._decode, encoded_results)

        return extract_record_set(records, filters, sorting,
                                  pagination_rules, limit)


def load_from_config(config):
    settings = config.registry.settings
    host = settings.get('redis.host', 'localhost')
    port = settings.get('redis.port', 6379)
    db = settings.get('redis.db', 0)
    return Redis(host=host, port=port, db=db)
