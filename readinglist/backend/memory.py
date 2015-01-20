import operator
from operator import itemgetter
from collections import defaultdict

from readinglist.backend import BackendBase, exceptions
from readinglist import utils
from readinglist.utils import COMPARISON, classname


tree = lambda: defaultdict(tree)


class Memory(BackendBase):
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self._store = tree()
        self._timestamps = defaultdict(dict)

    def flush(self):
        pass

    def ping(self):
        return True

    def timestamp(self, resource, user_id):
        resource_name = classname(resource)
        return self._timestamps[resource_name].get(user_id, utils.msec_time())

    def _bump_timestamp(self, resource_name, user_id):
        """Timestamp are base on current millisecond.

        .. note ::

            Here it is assumed that if requests from the same user burst in,
            the time will slide into the future. It is not problematic since
            the timestamp notion is opaque, and behaves like a revision number.
        """
        previous = self._timestamps[resource_name].get(user_id)
        current = utils.msec_time()
        if previous and previous >= current:
            current = previous + 1
        self._timestamps[resource_name][user_id] = current
        return current

    def create(self, resource, user_id, record):
        resource_name = classname(resource)
        _id = record[resource.id_field] = self.id_generator()
        timestamp = self._bump_timestamp(resource_name, user_id)
        record[resource.modified_field] = timestamp
        self._store[resource_name][user_id][_id] = record
        return record

    def get(self, resource, user_id, record_id):
        resource_name = classname(resource)
        collection = self._store[resource_name][user_id]
        if record_id not in collection:
            raise exceptions.RecordNotFoundError(record_id)
        return collection[record_id]

    def update(self, resource, user_id, record_id, record):
        resource_name = classname(resource)
        timestamp = self._bump_timestamp(resource_name, user_id)
        record[resource.modified_field] = timestamp
        self._store[resource_name][user_id][record_id] = record
        return record

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        existing = self.get(resource, user_id, record_id)
        self._bump_timestamp(resource_name, user_id)
        self._store[resource_name][user_id].pop(record_id)
        return existing

    def get_all(self, resource, user_id, filters=None, sorting=None):
        resource_name = classname(resource)
        records = self._store[resource_name][user_id].values()
        filtered = self.__apply_filters(records, filters or [])
        sorted_ = self.__apply_sorting(filtered, sorting or [])
        return sorted_

    def __apply_filters(self, records, filters):
        operators = {
            utils.COMPARISON.LT: operator.lt,
            utils.COMPARISON.MAX: operator.le,
            utils.COMPARISON.EQ: operator.eq,
            utils.COMPARISON.NOT: operator.ne,
            utils.COMPARISON.MIN: operator.ge,
            utils.COMPARISON.GT: operator.gt,
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


def load_from_config(config):
    return Memory()
