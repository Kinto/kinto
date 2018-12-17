import re
import operator
from collections import defaultdict
from collections import abc
import numbers

from kinto.core import utils
from kinto.core.decorators import synchronized
from kinto.core.storage import (
    StorageBase,
    exceptions,
    DEFAULT_ID_FIELD,
    DEFAULT_MODIFIED_FIELD,
    DEFAULT_DELETED_FIELD,
    MISSING,
)
from kinto.core.utils import COMPARISON, find_nested_value
from kinto.core.decorators import deprecate_kwargs

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

    def strip_deleted_object(
        self,
        resource_name,
        parent_id,
        obj,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
    ):
        """Strip the object of all its fields expect id and timestamp,
        and set the deletion field value (e.g deleted=True)
        """
        deleted = {}
        deleted[id_field] = obj[id_field]
        deleted[modified_field] = obj[modified_field]
        deleted[deleted_field] = True
        return deleted

    def set_object_timestamp(
        self,
        resource_name,
        parent_id,
        obj,
        modified_field=DEFAULT_MODIFIED_FIELD,
        last_modified=None,
    ):
        timestamp = self.bump_and_store_timestamp(
            resource_name, parent_id, obj, modified_field, last_modified=last_modified
        )
        obj[modified_field] = timestamp
        return obj

    def extract_object_set(
        self, objects, filters, sorting, id_field, deleted_field, pagination_rules=None, limit=None
    ):
        """Take the list of objects and handle filtering, sorting and
        pagination.

        """
        return extract_object_set(
            objects,
            filters=filters,
            sorting=sorting,
            id_field=id_field,
            deleted_field=deleted_field,
            pagination_rules=pagination_rules,
            limit=limit,
        )

    def bump_timestamp(self, resource_timestamp, obj, modified_field, last_modified):
        """Timestamp are base on current millisecond.

        .. note ::

            Here it is assumed that if requests from the same user burst in,
            the time will slide into the future. It is not problematic since
            the timestamp notion is opaque, and behaves like a revision number.
        """
        is_specified = obj is not None and modified_field in obj or last_modified is not None
        if is_specified:
            # If there is a timestamp in the new object, try to use it.
            if last_modified is not None:
                current = last_modified
            else:
                current = obj[modified_field]

            # If it is equal to current resource timestamp, bump it.
            if current == resource_timestamp:
                resource_timestamp += 1
                current = resource_timestamp
            # If it is superior (future), use it as new resource timestamp.
            elif current > resource_timestamp:
                resource_timestamp = current
            # Else (past), do nothing.

        else:
            # Not specified, use a new one.
            current = utils.msec_time()
            # If two ops in the same msec, bump it.
            if current <= resource_timestamp:
                current = resource_timestamp + 1
            resource_timestamp = current
        return current, resource_timestamp

    def bump_and_store_timestamp(
        self, resource_name, parent_id, obj=None, modified_field=None, last_modified=None
    ):
        """Use the bump_timestamp to get its next value and store the resource_timestamp.
        """
        raise NotImplementedError


class Storage(MemoryBasedStorage):
    """Storage backend implementation in memory.

    Useful for development or testing purposes, but stored data is lost after
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
    def resource_timestamp(self, resource_name, parent_id, auth=None):
        ts = self._timestamps[parent_id].get(resource_name)
        if ts is not None:
            return ts
        if self.readonly:
            error_msg = "Cannot initialize empty resource timestamp when running in readonly."
            raise exceptions.BackendError(message=error_msg)
        return self.bump_and_store_timestamp(resource_name, parent_id)

    def bump_and_store_timestamp(
        self, resource_name, parent_id, obj=None, modified_field=None, last_modified=None
    ):
        """Use the bump_timestamp to get its next value and store the resource_timestamp.
        """
        current_resource_timestamp = self._timestamps[parent_id].get(resource_name, 0)

        current, resource_timestamp = self.bump_timestamp(
            current_resource_timestamp, obj, modified_field, last_modified
        )
        self._timestamps[parent_id][resource_name] = resource_timestamp

        return current

    @deprecate_kwargs({"collection_id": "resource_name", "record": "obj"})
    @synchronized
    def create(
        self,
        resource_name,
        parent_id,
        obj,
        id_generator=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        id_generator = id_generator or self.id_generator
        obj = {**obj}
        if id_field in obj:
            # Raise unicity error if object with same id already exists.
            try:
                existing = self.get(resource_name, parent_id, obj[id_field])
                raise exceptions.UnicityError(id_field, existing)
            except exceptions.ObjectNotFoundError:
                pass
        else:
            obj[id_field] = id_generator()

        self.set_object_timestamp(resource_name, parent_id, obj, modified_field=modified_field)
        _id = obj[id_field]
        obj = ujson.loads(self.json.dumps(obj))
        self._store[parent_id][resource_name][_id] = obj
        self._cemetery[parent_id][resource_name].pop(_id, None)
        return obj

    @deprecate_kwargs({"collection_id": "resource_name"})
    @synchronized
    def get(
        self,
        resource_name,
        parent_id,
        object_id,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        objects = self._store[parent_id][resource_name]
        if object_id not in objects:
            raise exceptions.ObjectNotFoundError(object_id)
        return {**objects[object_id]}

    @deprecate_kwargs({"collection_id": "resource_name", "record": "obj"})
    @synchronized
    def update(
        self,
        resource_name,
        parent_id,
        object_id,
        obj,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        obj = {**obj}
        obj[id_field] = object_id
        obj = ujson.loads(self.json.dumps(obj))

        self.set_object_timestamp(resource_name, parent_id, obj, modified_field=modified_field)
        self._store[parent_id][resource_name][object_id] = obj
        self._cemetery[parent_id][resource_name].pop(object_id, None)
        return obj

    @deprecate_kwargs({"collection_id": "resource_name"})
    @synchronized
    def delete(
        self,
        resource_name,
        parent_id,
        object_id,
        id_field=DEFAULT_ID_FIELD,
        with_deleted=True,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
        last_modified=None,
    ):
        existing = self.get(resource_name, parent_id, object_id)
        # Need to delete the last_modified field of the object.
        del existing[modified_field]

        self.set_object_timestamp(
            resource_name,
            parent_id,
            existing,
            modified_field=modified_field,
            last_modified=last_modified,
        )
        existing = self.strip_deleted_object(resource_name, parent_id, existing)

        # Add to deleted items, remove from store.
        if with_deleted:
            deleted = {**existing}
            self._cemetery[parent_id][resource_name][object_id] = deleted
        self._store[parent_id][resource_name].pop(object_id)
        return existing

    @deprecate_kwargs({"collection_id": "resource_name"})
    @synchronized
    def purge_deleted(
        self,
        resource_name,
        parent_id,
        before=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        parent_id_match = re.compile(parent_id.replace("*", ".*"))
        by_parent_id = {
            pid: resources
            for pid, resources in self._cemetery.items()
            if parent_id_match.match(pid)
        }
        num_deleted = 0
        for pid, resources in by_parent_id.items():
            if resource_name is not None:
                resources = {resource_name: resources[resource_name]}
            for resource, resource_objects in resources.items():
                if before is None:
                    kept = {}
                else:
                    kept = {
                        key: value
                        for key, value in resource_objects.items()
                        if value[modified_field] >= before
                    }
                self._cemetery[pid][resource] = kept
                num_deleted += len(resource_objects) - len(kept)
        return num_deleted

    @synchronized
    def list_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):
        objects = _get_objects_by_parent_id(self._store, parent_id, resource_name)

        objects, _ = self.extract_object_set(
            objects=objects,
            filters=filters,
            sorting=None,
            id_field=id_field,
            deleted_field=deleted_field,
        )
        deleted = []
        if include_deleted:
            deleted = _get_objects_by_parent_id(self._cemetery, parent_id, resource_name)

        objects, _ = self.extract_object_set(
            objects=objects + deleted,
            filters=filters,
            sorting=sorting,
            id_field=id_field,
            deleted_field=deleted_field,
            pagination_rules=pagination_rules,
            limit=limit,
        )
        return objects

    @synchronized
    def count_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):
        objects = _get_objects_by_parent_id(self._store, parent_id, resource_name)
        _, count = self.extract_object_set(
            objects=objects,
            filters=filters,
            sorting=None,
            id_field=id_field,
            deleted_field=deleted_field,
        )
        return count

    @deprecate_kwargs({"collection_id": "resource_name"})
    @synchronized
    def delete_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        id_field=DEFAULT_ID_FIELD,
        with_deleted=True,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):
        objects = _get_objects_by_parent_id(self._store, parent_id, resource_name, with_meta=True)
        objects, count = self.extract_object_set(
            objects=objects,
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            id_field=id_field,
            deleted_field=deleted_field,
        )

        deleted = [
            self.delete(
                r.pop("__resource_name__"),
                r.pop("__parent_id__"),
                r[id_field],
                id_field=id_field,
                with_deleted=with_deleted,
                modified_field=modified_field,
                deleted_field=deleted_field,
            )
            for r in objects
        ]
        return deleted


def extract_object_set(
    objects,
    filters,
    sorting,
    pagination_rules=None,
    limit=None,
    id_field=DEFAULT_ID_FIELD,
    deleted_field=DEFAULT_DELETED_FIELD,
):
    """Apply filters, sorting, limit, and pagination rules to the list of
    `objects`.

    """
    filtered = list(apply_filters(objects, filters or []))
    total_objects = len(filtered)

    if pagination_rules:
        paginated = []
        for rule in pagination_rules:
            values = apply_filters(filtered, rule)
            paginated.extend(values)
    else:
        paginated = filtered

    sorted_ = apply_sorting(paginated, sorting or [])

    filtered_deleted = len([r for r in sorted_ if r.get(deleted_field) is True])

    if limit:
        sorted_ = list(sorted_)[:limit]

    return sorted_, total_objects - filtered_deleted


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def apply_filters(objects, filters):
    """Filter the specified objects, using basic iteration.
    """

    def contains_filtering(object_value, search_term):
        if object_value == MISSING:
            return False
        try:
            search_set = set([canonical_json(v) for v in search_term])
            object_value_set = set([canonical_json(v) for v in object_value])
        except TypeError:
            return False
        return object_value_set.intersection(search_set) == search_set

    def contains_any_filtering(object_value, search_term):
        if object_value == MISSING:
            return False
        try:
            search_set = set([canonical_json(v) for v in search_term])
            object_value_set = set([canonical_json(v) for v in object_value])
        except TypeError:
            return False
        return object_value_set.intersection(search_set)

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
    for obj in objects:
        matches = True
        for f in filters:
            right = f.value
            if f.field == DEFAULT_ID_FIELD:
                if isinstance(right, int):
                    right = str(right)

            left = find_nested_value(obj, f.field, MISSING)

            if f.operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                right, left = left, right
            elif f.operator == COMPARISON.LIKE:
                # Add implicit start/end wildchars if none is specified.
                if "*" not in right:
                    right = f"*{right}*"
                right = f"^{right.replace('*', '.*')}$"
            elif f.operator in (
                COMPARISON.LT,
                COMPARISON.MAX,
                COMPARISON.EQ,
                COMPARISON.NOT,
                COMPARISON.MIN,
                COMPARISON.GT,
            ):
                left = schwartzian_transform(left)
                right = schwartzian_transform(right)

            if f.operator == COMPARISON.HAS:
                matches = left != MISSING if f.value else left == MISSING
            else:
                matches = matches and operators[f.operator](left, right)
        if matches:
            yield obj


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
    raise ValueError(f"Unknown value: {value}")  # pragma: no cover


def apply_sorting(objects, sorting):
    """Sort the specified objects, using cumulative python sorting.
    """
    result = list(objects)

    if not result:
        return result

    def column(obj, name):
        return schwartzian_transform(find_nested_value(obj, name, default=MISSING))

    for sort in reversed(sorting):
        result = sorted(result, key=lambda r: column(r, sort.field), reverse=(sort.direction < 0))

    return result


def _get_objects_by_parent_id(store, parent_id, resource_name, with_meta=False):
    parent_id_match = re.compile(f"^{parent_id.replace('*', '.*')}$")
    by_parent_id = {
        pid: resources for pid, resources in store.items() if parent_id_match.match(pid)
    }
    objects = []
    for pid, resources in by_parent_id.items():
        if resource_name is not None:
            resources = {resource_name: resources[resource_name]}
        for resource, colobjects in resources.items():
            for r in colobjects.values():
                if with_meta:
                    objects.append(dict(__resource_name__=resource, __parent_id__=pid, **r))
                else:
                    objects.append(r)
    return objects


def load_from_config(config):
    settings = {**config.get_settings()}
    strict = settings.get("storage_strict_json", False)
    return Storage(strict_json=strict)
