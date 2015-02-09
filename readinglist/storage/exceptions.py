class RecordNotFoundError(Exception):
    pass


class IntegrityError(Exception):
    pass


class UnicityError(IntegrityError):
    def __init__(self, field, record, *args, **kwargs):
        self.field = field
        self.record = record
        super(UnicityError, self).__init__(self, *args, **kwargs)
