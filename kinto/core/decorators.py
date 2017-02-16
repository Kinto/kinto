import threading
from functools import update_wrapper
from pyramid.response import Response


class cache_forever:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.saved = None
        update_wrapper(self, wrapped)

    def __call__(self, request, *args, **kwargs):
        if self.saved is None:
            self.saved = self.wrapped(request, *args, **kwargs)
            if isinstance(self.saved, Response):
                self.saved = None
                raise ValueError('cache_forever cannot cache Response only its body')

        request.response.write(self.saved)
        return request.response


def synchronized(method):
    """Class method decorator to make sure two threads do not execute some code
    at the same time (c.f Java ``synchronized`` keyword).

    The decorator installs a mutex on the class instance.
    """
    def decorated(self, *args, **kwargs):
        try:
            lock = getattr(self, '__lock__')
        except AttributeError:
            lock = threading.RLock()
            setattr(self, '__lock__', lock)

        lock.acquire()
        try:
            result = method(self, *args, **kwargs)
        finally:
            lock.release()
        return result
    return decorated
