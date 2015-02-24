import operator
from cliquet.storage import exceptions
from cliquet.storage.id_generator import UUID4Generator
from cliquet.utils import COMPARISON


class StorageBase(object):
    """Storage abstraction used by resource views.

    It is meant to be instantiated at application startup.
    Any operation may raise a `HTTPServiceUnavailable` error if an error
    occurs with the underlying service.

    Configuration can be changed to choose which storage backend will
    persist the records.

    :raises: cliquet.errors.HTTPServiceUnavailable
    """
    def __init__(self, id_generator=None, *args, **kwargs):
        if id_generator is None:
            id_generator = UUID4Generator()
        self.id_generator = id_generator

    def flush(self):
        """Remove every record from the storage.
        """
        raise NotImplementedError

    def ping(self):
        """Test that storage is operationnal.

        :returns: `True` is everything is ok, `False` otherwise.
        :rtype: boolean
        """
        raise NotImplementedError

    def collection_timestamp(self, resource, user_id):
        """Get the highest timestamp of every records in this resource for
        this user.

        :note:
            This should take deleted records into account.

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :returns: the latest timestamp of the collection.
        :rtype: integer
        """
        raise NotImplementedError

    def create(self, resource, user_id, record):
        """Create the specified record in this resource for this user.
        Assign the id to the record, using the `resource.id_field` attribute.

        :note:
            This will update the collection timestamp.

        :raises: cliquet.storage.exceptions.UnicityError

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :param record: the record to create.
        :type record: dict

        :returns: the newly created record.
        :rtype: dict
        """
        raise NotImplementedError

    def get(self, resource, user_id, record_id):
        """Retrieve the record with specified id, or raise error if not found.

        :raises: cliquet.storage.exceptions.RecordNotFoundError

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :param record_id: unique identifier of the record
        :type user_id: unicode

        :returns: the record object.
        :rtype: dict
        """
        raise NotImplementedError

    def update(self, resource, user_id, record_id, record):
        """Overwrite the record with the specified id.

        If the specified id is not found, the record is created with the
        specified id.

        :note:
            This will update the collection timestamp.

        :raises: cliquet.storage.exceptions.UnicityError

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :param record_id: unique identifier of the record
        :type user_id: unicode

        :param record: the record to update or create.
        :type record: dict

        :returns: the updated record.
        :rtype: dict
        """
        raise NotImplementedError

    def delete(self, resource, user_id, record_id):
        """Delete the record with specified id, and raise error if not found.

        Deleted records must be removed from the database, but their ids and
        timestamps of deletion must be tracked for synchronization purposes
        (see `Storage.get_all()`).

        :note:
            This will update the collection timestamp.

        :raises: cliquet.storage.exceptions.RecordNotFoundError

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :param record_id: unique identifier of the record
        :type user_id: unicode

        :returns: the deleted record, with minimal set of attributes.
        :rtype: dict
        """
        raise NotImplementedError

    def delete_all(self, resource, user_id, filters=None):
        """Delete a set of records.

        XXX: Move this MemoryBasedStorage once PostgreSQL branch is merged.
        """
        records, count = self.get_all(resource, user_id, filters=filters)
        deleted = [self.delete(resource, user_id, r[resource.id_field])
                   for r in records]
        return deleted

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        """

        :param resource: the record associated resource
        :type resource: cliquer.resource.BaseResource

        :param user_id: the owner of the record
        :type user_id: unicode

        :param filters: Optionally filter the records by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `cliquet.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of tuples (field, value, operator)

        :param sorting: Optionnally sort the records by attribute.
            Each sort instruction in this list refers to a field and a
            direction (negative means descending). All sort instructions are
            cumulative.
        :type sorting: list of tuples

        :param pagination_rules: Optionnally paginate the list of records.
            This list of rules aims to reduce the set of records to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of tuples

        :param limit: Optionnally limit the number of records to be retrieved.
        :type limit: integer

        :param include_deleted: Optionnally include the deleted records that
            match the filters.
        :type include_deleted: boolean

        :returns: the limited list of records, and the total number of
            matching records in the collection (deleted ones excluded).
        :rtype: tuple (list, integer)
        """
        raise NotImplementedError

    def check_unicity(self, resource, user_id, record):
        """Check that the specified record does not violates unicity
        constraints defined in the resource's mapping options.
        """
        record_id = record.get(resource.id_field)
        unique_fields = resource.mapping.Options.unique_fields

        for field in unique_fields:
            value = record.get(field)
            filters = [(field, value, COMPARISON.EQ)]
            if record_id:
                filters += [(resource.id_field, record_id, COMPARISON.NOT)]

            if value is not None:
                existing, count = self.get_all(resource, user_id,
                                               filters=filters)
                if count > 0:
                    raise exceptions.UnicityError(field, existing[0])


class MemoryBasedStorage(StorageBase):

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
        matches = [operators[op](record.get(k), v) for k, v, op in filters]
        if all(matches):
            yield record


def apply_sorting(records, sorting):
    result = list(records)

    if not result:
        return result

    def column(record, name):
        empty = result[0].get(name, float('inf'))
        return record.get(name, empty)

    for field, direction in reversed(sorting):
        desc = direction < 0
        result = sorted(result, key=lambda r: column(r, field), reverse=desc)

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
