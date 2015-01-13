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

    def get_all(self, resource, user_id, filters=None):
        resource_name = classname(resource)
        records = self._store[resource_name][user_id].values()
        return [r for r in records if self.__matches_filters(r, filters)]

    def __matches_filters(self, record, filters):
        for k, v in filters.items():
            if record[k] != v:
                return False
        return True


def load_from_config(config):
    return Memory()
