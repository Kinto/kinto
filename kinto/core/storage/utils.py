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

    object_pagination = None
    while True:
        (objects, _) = storage.get_all(
            sorting=sorting, limit=batch_size, pagination_rules=object_pagination, **kwargs
        )

        if not objects:
            break

        for object in objects:
            yield object

        object_pagination = [
            # FIXME: support more than one-length sorting
            [Filter(sorting[0].field, object[sorting[0].field], pagination_direction)]
        ]
