from collections import defaultdict

from readinglist import utils
from readinglist.utils import classname

from readinglist.backend import (
    BackendBase, exceptions, apply_filters, apply_sorting
)


tree = lambda: defaultdict(tree)


class Memory(BackendBase):
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self.flush()

    def flush(self):
        self._store = tree()
        self._timestamps = defaultdict(dict)

    def ping(self):
        return True

    def last_collection_timestamp(self, resource, user_id):
        resource_name = classname(resource)
        return self._timestamps[resource_name].get(user_id, utils.msec_time())

    def _bump_timestamp(self, resource, user_id):
        """Timestamp are base on current millisecond.

        .. note ::

            Here it is assumed that if requests from the same user burst in,
            the time will slide into the future. It is not problematic since
            the timestamp notion is opaque, and behaves like a revision number.
        """
        resource_name = classname(resource)
        previous = self._timestamps[resource_name].get(user_id)
        current = utils.msec_time()
        if previous and previous >= current:
            current = previous + 1
        self._timestamps[resource_name][user_id] = current
        return current

    def create(self, resource, user_id, record):
        record = record.copy()
        resource_name = classname(resource)
        _id = record[resource.id_field] = self.id_generator()
        self.set_record_timestamp(resource, user_id, record)
        self._store[resource_name][user_id][_id] = record
        return record

    def get(self, resource, user_id, record_id):
        resource_name = classname(resource)
        collection = self._store[resource_name][user_id]
        if record_id not in collection:
            raise exceptions.RecordNotFoundError(record_id)
        return collection[record_id]

    def update(self, resource, user_id, record_id, record):
        record = record.copy()
        resource_name = classname(resource)
        self.set_record_timestamp(resource, user_id, record)
        record[resource.id_field] = record_id
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
        filtered = apply_filters(records, filters or [])
        sorted_ = apply_sorting(filtered, sorting or [])
        return sorted_


def load_from_config(config):
    return Memory()
