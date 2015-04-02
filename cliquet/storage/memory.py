import operator
import six
from collections import defaultdict
from uuid import uuid4

from cliquet import utils
from cliquet.storage import StorageBase, exceptions, Filter
from cliquet.utils import COMPARISON


class UUID4Generator(object):

    def __init__(self, config=None):
        pass

    def __call__(self, key_exist=None):
        return six.text_type(uuid4()).replace('-', '')


def tree():
    return defaultdict(tree)


class MemoryBasedStorage(StorageBase):
    """Abstract storage class, providing basic operations and
    methods for in-memory implementations of sorting and filtering.
    """

    def __init__(self, id_generator=None, *args, **kwargs):
        if id_generator is None:
            id_generator = UUID4Generator()
        self.id_generator = id_generator

    def initialize_schema(self):
        # Nothing to do.
        pass

    def delete_all(self, resource, user_id, filters=None):
        records, count = self.get_all(resource, user_id, filters=filters)
        deleted = [self.delete(resource, user_id, r[resource.id_field])
                   for r in records]
        return deleted

    def strip_deleted_record(self, resource, user_id, record):
        """Strip the record of all its fields expect id and timestamp,
        and set the deletion field value (e.g deleted=True)
        """
        deleted = {}
        deleted[resource.id_field] = record[resource.id_field]
        deleted[resource.modified_field] = record[resource.modified_field]

        deleted[resource.deleted_field] = True
        return deleted

    def set_record_timestamp(self, resource, user_id, record):
        timestamp = self._bump_timestamp(resource, user_id)
        record[resource.modified_field] = timestamp
        return record

    def check_unicity(self, resource, user_id, record):
        """Check that the specified record does not violates unicity
        constraints defined in the resource's mapping options.
        """
        unicity_rules = get_unicity_rules(resource, user_id, record)
        for filters in unicity_rules:
            existing, count = self.get_all(resource, user_id, filters=filters)
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

    def extract_record_set(self, resource, records, filters, sorting,
                           pagination_rules=None, limit=None):
        """Take the list of records and handle filtering, sorting and
        pagination.

        """
        filtered = list(self.apply_filters(records, filters or []))
        total_records = len(filtered)

        paginated = {}
        for rule in pagination_rules or []:
            values = list(self.apply_filters(filtered, rule))
            paginated.update(dict(((x[resource.id_field], x) for x in values)))

        if paginated:
            paginated = paginated.values()
        else:
            paginated = filtered

        sorted_ = self.apply_sorting(paginated, sorting or [])

        filtered_deleted = len([r for r in sorted_
                                if r.get(resource.deleted_field) is True])

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

    def flush(self):
        self._store = tree()
        self._cemetery = tree()
        self._timestamps = defaultdict(dict)

    def ping(self):
        return True

    def collection_timestamp(self, resource, user_id):
        ts = self._timestamps[resource.name].get(user_id)
        if ts is not None:
            return ts
        return self._bump_timestamp(resource, user_id)

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

        records, count = self.extract_record_set(resource,
                                                 records + deleted,
                                                 filters, sorting,
                                                 pagination_rules, limit)

        return records, count


def get_unicity_rules(resource, user_id, record):
    """Build filter to target existing records that violate the resource
    unicity rules on fields.

    :returns: a list of list of filters
    """
    record_id = record.get(resource.id_field)
    unique_fields = resource.mapping.get_option('unique_fields')

    rules = []
    for field in unique_fields:
        value = record.get(field)

        # None values cannot be considered unique
        if value is None:
            continue

        filters = [Filter(field, value, COMPARISON.EQ)]
        if record_id:
            exclude = Filter(resource.id_field, record_id, COMPARISON.NOT)
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
