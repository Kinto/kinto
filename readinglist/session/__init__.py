class SessionStorageBase(object):
    def __init__(self, *args, **kwargs):
        pass

    def flush(self):
        raise NotImplementedError

    def ping(self):
        raise NotImplementedError

    def ttl(self, key):
        raise NotImplementedError

    def expire(self, key, value):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError
