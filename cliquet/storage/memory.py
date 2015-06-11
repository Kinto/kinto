import operator
from collections import defaultdict

from cliquet import utils
from cliquet.storage import (
    StorageBase, exceptions, Filter,
    DEFAULT_ID_FIELD, DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD)
from cliquet.utils import COMPARISON


def tree():
    return defaultdict(tree)


class MemoryBasedStorage(StorageBase):
    """Abstract storage class, providing basic operations and
    methods for in-memory implementations of sorting and filtering.
    """
    def __init__(self, *args, **kwargs):
        pass

    def initialize_schema(self):
        # Nothing to do.
        pass

    def delete_all(self, collection_id, parent_id, filters=None,
                   id_field=DEFAULT_ID_FIELD,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        records, count = self.get_all(collection_id, parent_id,
                                      filters=filters,
                                      id_field=id_field,
                                      modified_field=modified_field,
                                      deleted_field=deleted_field)
        deleted = [self.delete(collection_id, parent_id, r[id_field],
                               id_field=id_field,
                               modified_field=modified_field,
                               deleted_field=deleted_field)
                   for r in records]
        return deleted

    def strip_deleted_record(self, resource, parent_id, record,
                             id_field=DEFAULT_ID_FIELD,
                             modified_field=DEFAULT_MODIFIED_FIELD,
                             deleted_field=DEFAULT_DELETED_FIELD):
        """Strip the record of all its fields expect id and timestamp,
        and set the deletion field value (e.g deleted=True)
        """
        deleted = {}
        deleted[id_field] = record[id_field]
        deleted[modified_field] = record[modified_field]

        deleted[deleted_field] = True
        return deleted

    def set_record_timestamp(self, collection_id, parent_id, record,
                             modified_field=DEFAULT_MODIFIED_FIELD):
        timestamp = self._bump_timestamp(collection_id, parent_id)
        record[modified_field] = timestamp
        return record

    def check_unicity(self, collection_id, parent_id, record,
                      unique_fields, id_field, for_creation=False):
        """Check that the specified record does not violates unicity
        constraints defined in the resource's mapping options.
        """
        if for_creation and id_field in record:
            # If id is provided by client, check that no record conflicts.
            unique_fields = (unique_fields or tuple()) + (id_field,)

        if not unique_fields:
            return

        unicity_rules = get_unicity_rules(collection_id, parent_id, record,
                                          unique_fields=unique_fields,
                                          id_field=id_field,
                                          for_creation=for_creation)
        for filters in unicity_rules:
            existing, count = self.get_all(collection_id, parent_id,
                                           filters=filters,
                                           id_field=id_field)
            if count > 0:
                field = filters[0].field
                raise exceptions.UnicityError(field, existing[0])

    def apply_filters(self, records, filters):
        """Filter the specified records, using basic iteration.
        """
        operators = {
            COMPARISON.LT: operator.lt,
            COMPARISON.MAX: operator.le,
            COMPARISON.EQ: operator.eq,
            COMPARISON.NOT: operator.ne,
            COMPARISON.MIN: operator.ge,
            COMPARISON.GT: operator.gt,
        }

        for record in records:
            matches = [operators[f.operator](record.get(f.field), f.value)
                       for f in filters]
            if all(matches):
                yield record

    def apply_sorting(self, records, sorting):
        """Sort the specified records, using cumulative python sorting.
        """
        return apply_sorting(records, sorting)

    def extract_record_set(self, collection_id, records,
                           filters, sorting, id_field, deleted_field,
                           pagination_rules=None, limit=None):
        """Take the list of records and handle filtering, sorting and
        pagination.

        """
        filtered = list(self.apply_filters(records, filters or []))
        total_records = len(filtered)

        paginated = {}
        for rule in pagination_rules or []:
            values = list(self.apply_filters(filtered, rule))
            paginated.update(dict(((x[id_field], x) for x in values)))

        if paginated:
            paginated = paginated.values()
        else:
            paginated = filtered

        sorted_ = self.apply_sorting(paginated, sorting or [])

        filtered_deleted = len([r for r in sorted_
                                if r.get(deleted_field) is True])

        if limit:
            sorted_ = list(sorted_)[:limit]

        return sorted_, total_records - filtered_deleted


class Memory(MemoryBasedStorage):
    """Storage backend implementation in memory.

    Useful for development or testing purposes, but records are lost after
    each server restart.

    Enable in configuration::

        cliquet.storage_backend = cliquet.storage.memory
    """
    def __init__(self, *args, **kwargs):
        super(Memory, self).__init__(*args, **kwargs)
        self.flush()

    def flush(self, auth=None):
        self._store = tree()
        self._cemetery = tree()
        self._timestamps = defaultdict(dict)

    def collection_timestamp(self, collection_id, parent_id, auth=None):
        ts = self._timestamps[collection_id].get(parent_id)
        if ts is not None:
            return ts
        return self._bump_timestamp(collection_id, parent_id)

    def _bump_timestamp(self, collection_id, parent_id):
        """Timestamp are base on current millisecond.

        .. note ::

            Here it is assumed that if requests from the same user burst in,
            the time will slide into the future. It is not problematic since
            the timestamp notion is opaque, and behaves like a revision number.
        """
        previous = self._timestamps[collection_id].get(parent_id)
        current = utils.msec_time()
        if previous and previous >= current:
            current = previous + 1
        self._timestamps[collection_id][parent_id] = current
        return current

    def create(self, collection_id, parent_id, record, id_generator=None,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD, auth=None):
        self.check_unicity(collection_id, parent_id, record,
                           unique_fields=unique_fields,
                           id_field=id_field,
                           for_creation=True)

        id_generator = id_generator or self.id_generator
        record = record.copy()
        _id = record.setdefault(id_field, id_generator())
        self.set_record_timestamp(collection_id, parent_id, record,
                                  modified_field=modified_field)
        self._store[collection_id][parent_id][_id] = record
        return record

    def get(self, collection_id, parent_id, object_id,
            id_field=DEFAULT_ID_FIELD,
            modified_field=DEFAULT_MODIFIED_FIELD,
            auth=None):
        collection = self._store[collection_id][parent_id]
        if object_id not in collection:
            raise exceptions.RecordNotFoundError(object_id)
        return collection[object_id]

    def update(self, collection_id, parent_id, object_id, record,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        record = record.copy()
        record[id_field] = object_id

        self.check_unicity(collection_id, parent_id, record,
                           unique_fields=unique_fields,
                           id_field=id_field)

        self.set_record_timestamp(collection_id, parent_id, record,
                                  modified_field=modified_field)
        self._store[collection_id][parent_id][object_id] = record
        return record

    def delete(self, collection_id, parent_id, object_id,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None):
        existing = self.get(collection_id, parent_id, object_id)
        self.set_record_timestamp(collection_id, parent_id, existing,
                                  modified_field=modified_field)
        existing = self.strip_deleted_record(collection_id,
                                             parent_id,
                                             existing)

        # Add to deleted items, remove from store.
        self._cemetery[collection_id][parent_id][object_id] = existing.copy()
        self._store[collection_id][parent_id].pop(object_id)

        return existing

    def get_all(self, collection_id, parent_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False,
                id_field=DEFAULT_ID_FIELD,
                modified_field=DEFAULT_MODIFIED_FIELD,
                deleted_field=DEFAULT_DELETED_FIELD,
                auth=None):
        records = list(self._store[collection_id][parent_id].values())

        deleted = []
        if include_deleted:
            deleted = list(self._cemetery[collection_id][parent_id].values())

        records, count = self.extract_record_set(collection_id,
                                                 records + deleted,
                                                 filters, sorting,
                                                 id_field, deleted_field,
                                                 pagination_rules, limit)

        return records, count


def get_unicity_rules(collection_id, parent_id, record, unique_fields,
                      id_field, for_creation):
    """Build filter to target existing records that violate the resource
    unicity rules on fields.

    :returns: a list of list of filters
    """
    rules = []
    for field in set(unique_fields):
        value = record.get(field)

        # None values cannot be considered unique.
        if value is None:
            continue

        filters = [Filter(field, value, COMPARISON.EQ)]

        if not for_creation:
            object_id = record[id_field]
            exclude = Filter(id_field, object_id, COMPARISON.NOT)
            filters.append(exclude)

        rules.append(filters)

    return rules


def apply_sorting(records, sorting):
    """Sort the specified records, using cumulative python sorting.
    """
    result = list(records)

    if not result:
        return result

    first_record = result[0]

    def column(first, record, name):
        empty = first.get(name, float('inf'))
        return record.get(name, empty)

    for sort in reversed(sorting):
        result = sorted(result,
                        key=lambda r: column(first_record, r, sort.field),
                        reverse=(sort.direction < 0))

    return result


def load_from_config(config):
    return Memory()
