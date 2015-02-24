import operator
from collections import namedtuple

from cliquet.storage import exceptions
from cliquet.storage.id_generator import UUID4Generator
from cliquet.utils import COMPARISON


Filter = namedtuple('Filter', ['field', 'value', 'operator'])
"""Filtering properties."""

Sort = namedtuple('Sort', ['field', 'direction'])
"""Sorting properties."""


class StorageBase(object):
    def __init__(self, id_generator=None, *args, **kwargs):
        if id_generator is None:
            id_generator = UUID4Generator()
        self.id_generator = id_generator

    def flush(self):
        raise NotImplementedError

    def ping(self):
        raise NotImplementedError

    def collection_timestamp(self, resource, user_id):
        raise NotImplementedError

    def create(self, resource, user_id, record):
        raise NotImplementedError

    def get(self, resource, user_id, record_id):
        raise NotImplementedError

    def update(self, resource, user_id, record_id, record):
        raise NotImplementedError

    def delete(self, resource, user_id, record_id):
        raise NotImplementedError

    def delete_all(self, resource, user_id, filters=None):
        """Delete all records in this resource for this user.

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :param filters: Optionnally filter the records to delete.
        :type filters: list of filters

        :returns: the list of deleted records, with minimal set of attributes.
        :rtype: list of dict
        """
        raise NotImplementedError

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None):
        raise NotImplementedError

    def check_unicity(self, resource, user_id, record):
        """Check that the specified record does not violates unicity
        constraints defined in the resource's mapping options.
        """
        record_id = record.get(resource.id_field)
        unique_fields = resource.mapping.Options.unique_fields

        for field in unique_fields:
            value = record.get(field)
            filters = [Filter(field, value, COMPARISON.EQ)]
            if record_id:
                exclude = Filter(resource.id_field, record_id, COMPARISON.NOT)
                filters.append(exclude)

            if value is not None:
                existing, count = self.get_all(resource, user_id,
                                               filters=filters)
                if count > 0:
                    raise exceptions.UnicityError(field, existing[0])


class MemoryBasedStorage(StorageBase):

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

        field, value = resource.deleted_mark
        deleted[field] = value

        return deleted

    def set_record_timestamp(self, resource, user_id, record):
        timestamp = self._bump_timestamp(resource, user_id)
        record[resource.modified_field] = timestamp
        return record

    def _bump_timestamp(self, resource, user_id):
        raise NotImplementedError


def apply_filters(records, filters):
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


def apply_sorting(records, sorting):
    result = list(records)

    if not result:
        return result

    def column(record, name):
        empty = result[0].get(name, float('inf'))
        return record.get(name, empty)

    for sort in reversed(sorting):
        result = sorted(result,
                        key=lambda r: column(r, sort.field),
                        reverse=(sort.direction < 0))

    return result


def extract_record_set(resource, records, filters, sorting,
                       pagination_rules=None, limit=None):
    """Take the list of records and handle filtering, sorting and pagination.

    """
    filtered = list(apply_filters(records, filters or []))
    total_records = len(filtered)

    paginated = {}
    for rule in pagination_rules or []:
        values = list(apply_filters(filtered, rule))
        paginated.update(dict(((x[resource.id_field], x) for x in values)))

    if paginated:
        paginated = paginated.values()
    else:
        paginated = filtered

    sorted_ = apply_sorting(paginated, sorting or [])

    field, value = resource.deleted_mark
    filtered_deleted = len([r for r in sorted_ if r.get(field) == value])

    if limit:
        sorted_ = list(sorted_)[:limit]

    return sorted_, total_records - filtered_deleted
