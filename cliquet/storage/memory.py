from collections import defaultdict

from cliquet import utils
from cliquet.storage import (
    MemoryBasedStorage, exceptions, extract_record_set
)


def tree():
    return defaultdict(tree)


class Memory(MemoryBasedStorage):
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self.flush()

    def flush(self):
        self._store = tree()
        self._cemetery = tree()
        self._timestamps = defaultdict(dict)

    def ping(self):
        return True

    def collection_timestamp(self, resource, user_id):
        return self._timestamps[resource.name].get(user_id, utils.msec_time())

    def _bump_timestamp(self, resource, user_id):
        """Timestamp are base on current millisecond.

        .. note ::

            Here it is assumed that if requests from the same user burst in,
            the time will slide into the future. It is not problematic since
            the timestamp notion is opaque, and behaves like a revision number.
        """
        previous = self._timestamps[resource.name].get(user_id)
        current = utils.msec_time()
        if previous and previous >= current:
            current = previous + 1
        self._timestamps[resource.name][user_id] = current
        return current

    def create(self, resource, user_id, record):
        self.check_unicity(resource, user_id, record)

        record = record.copy()
        _id = record[resource.id_field] = self.id_generator()
        self.set_record_timestamp(resource, user_id, record)
        self._store[resource.name][user_id][_id] = record
        return record

    def get(self, resource, user_id, record_id):
        collection = self._store[resource.name][user_id]
        if record_id not in collection:
            raise exceptions.RecordNotFoundError(record_id)
        return collection[record_id]

    def update(self, resource, user_id, record_id, record):
        record = record.copy()
        record[resource.id_field] = record_id
        self.check_unicity(resource, user_id, record)

        self.set_record_timestamp(resource, user_id, record)
        self._store[resource.name][user_id][record_id] = record
        return record

    def delete(self, resource, user_id, record_id):
        existing = self.get(resource, user_id, record_id)
        self.set_record_timestamp(resource, user_id, existing)
        existing = self.strip_deleted_record(resource, user_id, existing)

        # Add to deleted items, remove from store.
        self._cemetery[resource.name][user_id][record_id] = existing.copy()
        self._store[resource.name][user_id].pop(record_id)

        return existing

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        records = list(self._store[resource.name][user_id].values())

        deleted = []
        if include_deleted:
            deleted = list(self._cemetery[resource.name][user_id].values())

        records, count = extract_record_set(resource,
                                            records + deleted,
                                            filters, sorting,
                                            pagination_rules, limit)

        return records, count


def load_from_config(config):
    return Memory()
