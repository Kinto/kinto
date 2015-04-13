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
            message = "%s: %s" % (original.__class__.__name__,
                                  original)
        super(BackendError, self).__init__(message, *args, **kwargs)


class RecordNotFoundError(Exception):
    """An exception raised when a specific record could not be found.

    """
    pass


class IntegrityError(Exception):
    pass


class UnicityError(IntegrityError):
    """An exception raised on unicity constraint violation.

    Raised by storage backend when the creation or the modification of a
    record violates the unicity constraints defined by the resource.

    """
    def __init__(self, field, record, *args, **kwargs):
        self.field = field
        self.record = record
        self.msg = "{0} is not unique: {1}".format(field, record)
        super(UnicityError, self).__init__(*args, **kwargs)
