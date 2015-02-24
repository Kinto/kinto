"""Exceptions raised by storage backend.
"""


class RecordNotFoundError(Exception):
    """An exception raised by storage backend when a specific record
    could not be found."""
    pass


class IntegrityError(Exception):
    pass


class UnicityError(IntegrityError):
    """An exception raised by storage backend when the creation or the
    modification of a record violates the unicity constraints defined by
    the resource."""
    def __init__(self, field, record, *args, **kwargs):
        self.field = field
        self.record = record
        super(UnicityError, self).__init__(*args, **kwargs)
