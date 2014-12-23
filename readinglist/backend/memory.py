from collections import defaultdict

from readinglist.backend import BackendBase, exceptions


tree = lambda: defaultdict(tree)


class Memory(BackendBase):
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self._store = tree()

    def flush(self):
        pass

    def create(self, resource, user_id, record):
        _id = record['_id'] = self.id_generator()
        self._store[resource][user_id][_id] = record
        return record

    def get(self, resource, user_id, record_id):
        collection = self._store[resource][user_id]
        if record_id not in collection:
            raise exceptions.RecordNotFoundError(record_id)
        return collection[record_id]

    def update(self, resource, user_id, record_id, record):
        self._store[resource][user_id][record_id] = record
        return record

    def delete(self, resource, user_id, record_id):
        existing = self.get(resource, user_id, record_id)
        self._store[resource][user_id].pop(record_id)
        return existing

    def get_all(self, resource, user_id):
        return self._store[resource][user_id].values()


def load_from_config(config):
    return Memory()
