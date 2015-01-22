from readinglist.backend.id_generator import UUID4Generator


class BackendBase(object):
    def __init__(self, id_generator=None):
        if id_generator is None:
            id_generator = UUID4Generator()
        self.id_generator = id_generator

    def flush(self):
        raise NotImplementedError

    def ping(self):
        raise NotImplementedError

    def now(self):
        raise NotImplementedError

    def create(self, resource, user_id, record):
        raise NotImplementedError

    def get(self, resource, user_id, record_id):
        raise NotImplementedError

    def update(self, resource, user_id, record_id, record):
        raise NotImplementedError

    def delete(self, resource, user_id, record_id):
        raise NotImplementedError

    def get_all(self, resource, user_id, filters=None, sorting=None):
        raise NotImplementedError
