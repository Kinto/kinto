from operator import itemgetter
from collections import defaultdict

from readinglist.backend import BackendBase, exceptions


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
        filtered = self.__apply_filters(records, filters or {})
        sorted_ = self.__apply_sorting(filtered, sorting or {})
        return sorted_

    def __apply_filters(self, records, filters):
        for record in records:
            matches = [record[k] == v for k, v in filters.items()]
            if all(matches):
                yield record

    def __apply_sorting(self, records, sorting):
        fields = sorting.keys()
        if len(fields) > 0:
            desc = list(sorting.values())[0] < 0  # XXX: reversed limited to 1
            records = sorted(records, key=itemgetter(*fields), reverse=desc)
        return list(records)


def load_from_config(config):
    return Memory()
