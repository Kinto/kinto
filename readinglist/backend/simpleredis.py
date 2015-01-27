import json
import redis
import time

from readinglist.backend import (
    BackendBase, exceptions, apply_filters, apply_sorting
)

from readinglist.utils import classname


class Redis(BackendBase):

    def __init__(self, *args, **kwargs):
        super(Redis, self).__init__(*args, **kwargs)
        self._client = redis.StrictRedis(**kwargs)

    def _encode(self, record):
        return json.dumps(record)

    def _decode(self, record):
        return json.loads(record)

    def flush(self):
        self._client.flushdb()

    def ping(self):
        try:
            self._client.setex('heartbeat', 3600, time.time())
            return True
        except redis.RedisError:
            return False

    def create(self, resource, user_id, record):
        resource_name = classname(resource)
        _id = record[resource.id_field] = self.id_generator()
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
        resource_name = classname(resource)
        record[resource.id_field] = record_id

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

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        with self._client.pipeline() as multi:
            multi.delete(
                '{0}.{1}.{2}'.format(resource_name, user_id, record_id))

            multi.srem(
                '{0}.{1}'.format(resource_name, user_id),
                record_id
            )
            responses = multi.execute()

            if responses[1] is not 1:
                raise exceptions.RecordNotFoundError(record_id)

    def get_all(self, resource, user_id, filters=None, sorting=None):
        resource_name = classname(resource)
        ids = self._client.smembers('{0}.{1}'.format(resource_name, user_id))

        if (len(ids) == 0):
            return []

        keys = ('{0}.{1}.{2}'.format(resource_name, user_id, _id) for _id in ids)


        encoded_results = self._client.mget(keys)
        records = map(self._decode, encoded_results)

        filtered = apply_filters(records, filters or [])
        sorted_ = apply_sorting(filtered, sorting or [])
        return sorted_


def load_from_config(config):
    settings = config.registry.settings
    host = settings.get('redis.host', 'localhost')
    port = settings.get('redis.port', 6379)
    db = settings.get('redis.db', 0)
    return Redis(host=host, port=port, db=db)
