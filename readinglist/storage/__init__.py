import operator
from readinglist.storage import exceptions
from readinglist.storage.id_generator import UUID4Generator
from readinglist.utils import COMPARISON


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

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None):
        raise NotImplementedError

    def set_record_timestamp(self, resource, user_id, record):
        timestamp = self._bump_timestamp(resource, user_id)
        record[resource.modified_field] = timestamp
        return record

    def check_unicity(self, resource, user_id, record):
        """Check that the specified record does not violates unicity
        constraints defined in the resource's mapping options.
        """
        record_id = record.get(resource.id_field)
        unique_fields = resource.mapping.Options.unique_fields

        for field in unique_fields:
            value = record.get(field)
            filters = [(field, value, COMPARISON.EQ),
                       (resource.id_field, record_id, COMPARISON.NOT)]

            if value is not None:
                existing, count = self.get_all(resource, user_id,
                                               filters=filters)
                if count > 0:
                    raise exceptions.UnicityError(field, existing[0])


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
        matches = [operators[op](record[k], v) for k, v, op in filters]
        if all(matches):
            yield record


def apply_sorting(records, sorting):
    result = list(records)

    if not result:
        return result

    for field, direction in reversed(sorting):
        is_boolean_field = isinstance(result[0][field], bool)
        desc = direction < 0 or is_boolean_field
        result = sorted(result, key=operator.itemgetter(field), reverse=desc)

    return result


def extract_record_set(records, filters, sorting,
                       pagination_rules=None, limit=None):
    """Take the list of records and handle filtering, sorting and pagination.

    """
    if not pagination_rules:
        pagination_rules = []
    filtered = list(apply_filters(records, filters or []))
    total_records = len(filtered)

    paginated = {}
    for rule in pagination_rules:
        values = list(apply_filters(filtered, rule))
        paginated.update(dict(((x['id'], x) for x in values)))

    if paginated:
        paginated = paginated.values()
    else:
        paginated = filtered

    sorted_ = apply_sorting(paginated, sorting or [])

    if limit:
        sorted_ = list(sorted_)[:limit]

    return sorted_, total_records
