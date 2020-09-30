"""Exceptions raised by storage backend.
"""


class BackendError(Exception):
    """A generic exception raised by storage on error.

    :param Exception original: the wrapped exception raised by underlying
        library.
    """

    def __init__(self, original=None, message=None, *args, **kwargs):
        self.original = original
        if message is None:
            message = f"{original.__class__.__name__}: {original}"
        super().__init__(message, *args, **kwargs)


class ReadonlyError(BackendError):
    """An error raised when a write operation is attempted on a
    read-only instance.
    """

    pass


class RecordNotFoundError(Exception):
    """Deprecated exception name."""

    pass


class ObjectNotFoundError(RecordNotFoundError):
    """An exception raised when a specific object could not be found."""

    pass


class IntegrityError(BackendError):
    pass


class UnicityError(IntegrityError):
    """An exception raised on unicity constraint violation.

    Raised by storage backend when the creation or the modification of a
    object violates the unicity constraints defined by the resource.

    """

    def __init__(self, field, *args, **kwargs):
        self.field = field
        self.msg = f"{field} is not unique"
        super().__init__(*args, **kwargs)
