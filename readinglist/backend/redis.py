import cjson
import redis
import time

from readinglist.backend import BackendBase, exceptions
from readinglist.utils import classname


class Redis(BackendBase):

    def __init__(self, *args, **kwargs):
        super(Redis, self).__init__(*args, **kwargs)
        self._client = redis.StrictRedis(**kwargs)

    def _encode(self, record):
        return cjson.encode(record)

    def _decode(self, record):
        return cjson.decode(record)

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
                '{0}.{1}.{1}'.format(resource_name, user_id, _id),
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

        return self._decode(self._client.get(
            '{0}.{1}.{2}'.format(resource_name, user_id, record_id))
        )

    def update(self, resource, user_id, record_id, record):
        resource_name = classname(resource)
        self._client.set(
            '{0}.{1}.{1}'.format(resource_name, user_id, record_id),
            self._encode(record)
        )

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        with self._client.pipeline() as multi:
            multi.delete(
                '{0}.{1}.{1}'.format(resource_name, user_id, record_id))

            multi.srem(
                '{0}.{1}'.format(resource_name, user_id),
                record_id
            )
            responses = multi.execute()

        return responses[1] == 1

    def get_all(self, resource, user_id, filters=None, sorting=None):
        resource_name = classname(resource)
        records = self._store[resource_name][user_id].values()
        filtered = self.__apply_filters(records, filters or [])
        sorted_ = self.__apply_sorting(filtered, sorting or [])
        return sorted_

    def __apply_filters(self, records, filters):
        operators = {
            '<': operator.lt,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne,
            '>=': operator.ge,
            '>': operator.gt,
        }
        for record in records:
            matches = [operators[op](record[k], v) for k, v, op in filters]
            if all(matches):
                yield record

    def __apply_sorting(self, records, sorting):
        result = list(records)

        if not result:
            return result

        for field, direction in reversed(sorting):
            is_boolean_field = isinstance(result[0][field], bool)
            reverse = direction < 0 or is_boolean_field
            result = sorted(result, key=itemgetter(field), reverse=reverse)

        return result
