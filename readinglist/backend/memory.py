import operator
from operator import itemgetter
from collections import defaultdict

from readinglist.backend import BackendBase, exceptions
from readinglist.utils import COMPARISON
from readinglist.utils import timestamper


tree = lambda: defaultdict(tree)
classname = lambda c: c.__class__.__name__.lower()


class Memory(BackendBase):
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self._store = tree()

    def flush(self):
        pass

    def ping(self):
        return True

    def now(self):
        return timestamper.now()

    def create(self, resource, user_id, record):
        resource_name = classname(resource)
        _id = record[resource.id_field] = self.id_generator()
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
        self._store[resource_name][user_id][record_id] = record
        return record

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        existing = self.get(resource, user_id, record_id)
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
            COMPARISON.LT: operator.lt,
            COMPARISON.MAX: operator.le,
            COMPARISON.EQ: operator.eq,
            COMPARISON.NOT: operator.ne,
            COMPARISON.MIN: operator.ge,
            COMPARISON.GT: operator.gt,
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
