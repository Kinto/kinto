"""
kinto.core.storage.utils: methods for making it easier to work with kinto storage objects
"""
from kinto.core.storage import Filter
from kinto.core.utils import COMPARISON

BATCH_SIZE = 25


def paginated(storage, *args, sorting, batch_size=BATCH_SIZE, **kwargs):
    """A generator used to access paginated results from storage.get_all.

    :param kwargs: Passed through unchanged to get_all.
    """

    if len(sorting) > 1:
        raise NotImplementedError("FIXME: only supports one-length sorting")  # pragma: nocover
    pagination_direction = COMPARISON.GT if sorting[0].direction > 0 else COMPARISON.LT

    record_pagination = None
    while True:
        (records, _) = storage.get_all(sorting=sorting, limit=batch_size,
                                       pagination_rules=record_pagination,
                                       **kwargs)

        if not records:
            break

        for record in records:
            yield record

        record_pagination = [
            # FIXME: support more than one-length sorting
            [Filter(sorting[0].field, record[sorting[0].field], pagination_direction)]
        ]
