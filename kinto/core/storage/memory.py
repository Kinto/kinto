import re
import operator
from collections import defaultdict
from collections import abc
import numbers

from kinto.core import utils
from kinto.core.decorators import synchronized
from kinto.core.storage import (
    StorageBase, exceptions,
    DEFAULT_ID_FIELD, DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD,
    MISSING)
from kinto.core.utils import (COMPARISON, find_nested_value)

import json
import ujson


def tree():
    return defaultdict(tree)


class MemoryBasedStorage(StorageBase):
    """Abstract storage class, providing basic operations and
    methods for in-memory implementations of sorting and filtering.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_schema(self, dry_run=False):
        # Nothing to do.
        pass

    def strip_deleted_record(self, collection_id, parent_id, record,
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
                             modified_field=DEFAULT_MODIFIED_FIELD,
                             last_modified=None):
        timestamp = self.bump_and_store_timestamp(collection_id, parent_id, record,
                                                  modified_field,
                                                  last_modified=last_modified)
        record[modified_field] = timestamp
        return record

    def extract_record_set(self, records,
                           filters, sorting, id_field, deleted_field,
                           pagination_rules=None, limit=None):
        """Take the list of records and handle filtering, sorting and
        pagination.

        """
        return extract_record_set(records,
                                  filters=filters,
                                  sorting=sorting,
                                  id_field=id_field,
                                  deleted_field=deleted_field,
                                  pagination_rules=pagination_rules,
                                  limit=limit)

    def bump_timestamp(self, collection_timestamp,
                       record, modified_field, last_modified):
        """Timestamp are base on current millisecond.

        .. note ::

            Here it is assumed that if requests from the same user burst in,
            the time will slide into the future. It is not problematic since
            the timestamp notion is opaque, and behaves like a revision number.
        """
        is_specified = (record is not None and
                        modified_field in record or
                        last_modified is not None)
        if is_specified:
            # If there is a timestamp in the new record, try to use it.
            if last_modified is not None:
                current = last_modified
            else:
                current = record[modified_field]

            # If it is equal to current collection timestamp, bump it.
            if current == collection_timestamp:
                collection_timestamp += 1
                current = collection_timestamp
            # If it is superior (future), use it as new collection timestamp.
            elif current > collection_timestamp:
                collection_timestamp = current
            # Else (past), do nothing.

        else:
            # Not specified, use a new one.
            current = utils.msec_time()
            # If two ops in the same msec, bump it.
            if current <= collection_timestamp:
                current = collection_timestamp + 1
            collection_timestamp = current
        return current, collection_timestamp

    def bump_and_store_timestamp(self, collection_id, parent_id, record=None,
                                 modified_field=None, last_modified=None):
        """Use the bump_timestamp to get its next value and store the collection_timestamp.
        """
        raise NotImplementedError


class Storage(MemoryBasedStorage):
    """Storage backend implementation in memory.

    Useful for development or testing purposes, but records are lost after
    each server restart.

    Enable in configuration::

        kinto.storage_backend = kinto.core.storage.memory

    Enable strict json validation before saving (instead of the more lenient
    ujson, see #1238)::

        kinto.storage_strict_json = true
    """
    def __init__(self, *args, readonly=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.readonly = readonly
        self.flush()

    def flush(self, auth=None):
        self._store = tree()
        self._cemetery = tree()
        self._timestamps = defaultdict(dict)

    @synchronized
    def collection_timestamp(self, collection_id, parent_id, auth=None):
        ts = self._timestamps[parent_id].get(collection_id)
        if ts is not None:
            return ts
        if self.readonly:
            error_msg = 'Cannot initialize empty collection timestamp when running in readonly.'
            raise exceptions.BackendError(message=error_msg)
        return self.bump_and_store_timestamp(collection_id, parent_id)

    def bump_and_store_timestamp(self, collection_id, parent_id, record=None,
                                 modified_field=None, last_modified=None):
        """Use the bump_timestamp to get its next value and store the collection_timestamp.
        """
        current_collection_timestamp = self._timestamps[parent_id].get(collection_id, 0)

        current, collection_timestamp = self.bump_timestamp(
            current_collection_timestamp,
            record, modified_field,
            last_modified)
        self._timestamps[parent_id][collection_id] = collection_timestamp

        return current

    @synchronized
    def create(self, collection_id, parent_id, record, id_generator=None,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD, auth=None):
        id_generator = id_generator or self.id_generator
        record = {**record}
        if id_field in record:
            # Raise unicity error if record with same id already exists.
            try:
                existing = self.get(collection_id, parent_id, record[id_field])
                raise exceptions.UnicityError(id_field, existing)
            except exceptions.RecordNotFoundError:
                pass
        else:
            record[id_field] = id_generator()

        self.set_record_timestamp(collection_id, parent_id, record,
                                  modified_field=modified_field)
        _id = record[id_field]
        record = ujson.loads(self.json.dumps(record))
        self._store[parent_id][collection_id][_id] = record
        self._cemetery[parent_id][collection_id].pop(_id, None)
        return record

    @synchronized
    def get(self, collection_id, parent_id, object_id,
            id_field=DEFAULT_ID_FIELD,
            modified_field=DEFAULT_MODIFIED_FIELD,
            auth=None):
        collection = self._store[parent_id][collection_id]
        if object_id not in collection:
            raise exceptions.RecordNotFoundError(object_id)
        return {**collection[object_id]}

    @synchronized
    def update(self, collection_id, parent_id, object_id, record,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        record = {**record}
        record[id_field] = object_id
        record = ujson.loads(self.json.dumps(record))

        self.set_record_timestamp(collection_id, parent_id, record,
                                  modified_field=modified_field)
        self._store[parent_id][collection_id][object_id] = record
        self._cemetery[parent_id][collection_id].pop(object_id, None)
        return record

    @synchronized
    def delete(self, collection_id, parent_id, object_id,
               id_field=DEFAULT_ID_FIELD, with_deleted=True,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None, last_modified=None):
        existing = self.get(collection_id, parent_id, object_id)
        # Need to delete the last_modified field of the record.
        del existing[modified_field]

        self.set_record_timestamp(collection_id, parent_id, existing,
                                  modified_field=modified_field,
                                  last_modified=last_modified)
        existing = self.strip_deleted_record(collection_id,
                                             parent_id,
                                             existing)

        # Add to deleted items, remove from store.
        if with_deleted:
            deleted = {**existing}
            self._cemetery[parent_id][collection_id][object_id] = deleted
        self._store[parent_id][collection_id].pop(object_id)
        return existing

    @synchronized
    def purge_deleted(self, collection_id, parent_id, before=None,
                      id_field=DEFAULT_ID_FIELD,
                      modified_field=DEFAULT_MODIFIED_FIELD,
                      auth=None):
        parent_id_match = re.compile(parent_id.replace('*', '.*'))
        by_parent_id = {pid: collections
                        for pid, collections in self._cemetery.items()
                        if parent_id_match.match(pid)}
        num_deleted = 0
        for pid, collections in by_parent_id.items():
            if collection_id is not None:
                collections = {collection_id: collections[collection_id]}
            for collection, colrecords in collections.items():
                if before is None:
                    kept = {}
                else:
                    kept = {key: value for key, value in
                            colrecords.items()
                            if value[modified_field] >= before}
                self._cemetery[pid][collection] = kept
                num_deleted += (len(colrecords) - len(kept))
        return num_deleted

    @synchronized
    def get_all(self, collection_id, parent_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False,
                id_field=DEFAULT_ID_FIELD,
                modified_field=DEFAULT_MODIFIED_FIELD,
                deleted_field=DEFAULT_DELETED_FIELD,
                auth=None):

        records = _get_objects_by_parent_id(self._store, parent_id, collection_id)

        records, count = self.extract_record_set(records=records,
                                                 filters=filters, sorting=None,
                                                 id_field=id_field, deleted_field=deleted_field)
        deleted = []
        if include_deleted:
            deleted = _get_objects_by_parent_id(self._cemetery, parent_id, collection_id)

        records, count = self.extract_record_set(records=records + deleted,
                                                 filters=filters, sorting=sorting,
                                                 id_field=id_field, deleted_field=deleted_field,
                                                 pagination_rules=pagination_rules, limit=limit)
        return records, count

    @synchronized
    def delete_all(self, collection_id, parent_id, filters=None,
                   sorting=None, pagination_rules=None, limit=None,
                   id_field=DEFAULT_ID_FIELD, with_deleted=True,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        records = _get_objects_by_parent_id(self._store, parent_id, collection_id, with_meta=True)
        records, count = self.extract_record_set(records=records,
                                                 filters=filters,
                                                 sorting=sorting,
                                                 pagination_rules=pagination_rules, limit=limit,
                                                 id_field=id_field,
                                                 deleted_field=deleted_field)

        deleted = [self.delete(r.pop('__collection_id__'),
                               r.pop('__parent_id__'),
                               r[id_field],
                               id_field=id_field, with_deleted=with_deleted,
                               modified_field=modified_field,
                               deleted_field=deleted_field)
                   for r in records]
        return deleted


def extract_record_set(records, filters, sorting,
                       pagination_rules=None, limit=None,
                       id_field=DEFAULT_ID_FIELD,
                       deleted_field=DEFAULT_DELETED_FIELD):
    """Apply filters, sorting, limit, and pagination rules to the list of
    `records`.

    """
    filtered = list(apply_filters(records, filters or []))
    total_records = len(filtered)

    if pagination_rules:
        paginated = []
        for rule in pagination_rules:
            values = apply_filters(filtered, rule)
            paginated.extend(values)
    else:
        paginated = filtered

    sorted_ = apply_sorting(paginated, sorting or [])

    filtered_deleted = len([r for r in sorted_
                            if r.get(deleted_field) is True])

    if limit:
        sorted_ = list(sorted_)[:limit]

    return sorted_, total_records - filtered_deleted


def canonical_json(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':'))


def apply_filters(records, filters):
    """Filter the specified records, using basic iteration.
    """

    def contains_filtering(record_value, search_term):
        if record_value == MISSING:
            return False
        try:
            search_set = set([canonical_json(v) for v in search_term])
            record_value_set = set([canonical_json(v) for v in record_value])
        except TypeError:
            return False
        return record_value_set.intersection(search_set) == search_set

    def contains_any_filtering(record_value, search_term):
        if record_value == MISSING:
            return False
        try:
            search_set = set([canonical_json(v) for v in search_term])
            record_value_set = set([canonical_json(v) for v in record_value])
        except TypeError:
            return False
        return record_value_set.intersection(search_set)

    operators = {
        COMPARISON.LT: operator.lt,
        COMPARISON.MAX: operator.le,
        COMPARISON.EQ: operator.eq,
        COMPARISON.NOT: operator.ne,
        COMPARISON.MIN: operator.ge,
        COMPARISON.GT: operator.gt,
        COMPARISON.IN: operator.contains,
        COMPARISON.EXCLUDE: lambda x, y: not operator.contains(x, y),
        COMPARISON.LIKE: lambda x, y: re.search(y, x, re.IGNORECASE),
        COMPARISON.CONTAINS: contains_filtering,
        COMPARISON.CONTAINS_ANY: contains_any_filtering,
    }
    for record in records:
        matches = True
        for f in filters:
            right = f.value
            if f.field == DEFAULT_ID_FIELD:
                if isinstance(right, int):
                    right = str(right)

            left = find_nested_value(record, f.field, MISSING)

            if f.operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                right, left = left, right
            elif f.operator == COMPARISON.LIKE:
                # Add implicit start/end wildchars if none is specified.
                if '*' not in right:
                    right = '*{}*'.format(right)
                right = '^{}$'.format(right.replace('*', '.*'))
            elif f.operator in (COMPARISON.LT, COMPARISON.MAX, COMPARISON.EQ,
                                COMPARISON.NOT, COMPARISON.MIN, COMPARISON.GT):
                left = schwartzian_transform(left)
                right = schwartzian_transform(right)

            if f.operator == COMPARISON.HAS:
                matches = left != MISSING if f.value else left == MISSING
            else:
                matches = matches and operators[f.operator](left, right)
        if matches:
            yield record


def schwartzian_transform(value):
    """Decorate a value with a tag that enforces the Postgres sort order.

    The sort order, per https://www.postgresql.org/docs/9.6/static/datatype-json.html, is:

    Object > Array > Boolean > Number > String > Null

    Note that there are more interesting rules for comparing objects
    and arrays but we probably don't need to be that compatible.

    MISSING represents what would be a SQL NULL, which is "bigger"
    than everything else.
    """
    if value is None:
        return (0, value)
    if isinstance(value, str):
        return (1, value)
    if isinstance(value, bool):
        # This has to be before Number, because bools are a subclass
        # of int :(
        return (3, value)
    if isinstance(value, numbers.Number):
        return (2, value)
    if isinstance(value, abc.Sequence):
        return (4, value)
    if isinstance(value, abc.Mapping):
        return (5, value)
    if value is MISSING:
        return (6, value)
    raise ValueError('Unknown value: {}'.format(value))   # pragma: no cover


def apply_sorting(records, sorting):
    """Sort the specified records, using cumulative python sorting.
    """
    result = list(records)

    if not result:
        return result

    def column(record, name):
        return schwartzian_transform(find_nested_value(record, name, default=MISSING))

    for sort in reversed(sorting):
        result = sorted(result,
                        key=lambda r: column(r, sort.field),
                        reverse=(sort.direction < 0))

    return result


def _get_objects_by_parent_id(store, parent_id, collection_id, with_meta=False):
    if parent_id is not None:
        parent_id_match = re.compile('^{}$'.format(parent_id.replace('*', '.*')))
        by_parent_id = {pid: collections
                        for pid, collections in store.items()
                        if parent_id_match.match(pid)}
    else:
        by_parent_id = store[parent_id]

    objects = []
    for pid, collections in by_parent_id.items():
        if collection_id is not None:
            collections = {collection_id: collections[collection_id]}
        for collection, colobjects in collections.items():
            for r in colobjects.values():
                if with_meta:
                    objects.append(dict(__collection_id__=collection,
                                        __parent_id__=pid, **r))
                else:
                    objects.append(r)
    return objects


def load_from_config(config):
    settings = {**config.get_settings()}
    strict = settings.get('storage_strict_json', False)
    return Storage(strict_json=strict)
