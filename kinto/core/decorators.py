import threading
import warnings
from functools import update_wrapper, wraps

from pyramid.response import Response


class cache_forever:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.saved = None
        self.saved_headers = None
        update_wrapper(self, wrapped)

    def __call__(self, request, *args, **kwargs):
        if self.saved is None:
            self.saved = self.wrapped(request, *args, **kwargs)
            self.saved_headers = request.response.headers
            if isinstance(self.saved, Response):
                self.saved = None
                raise ValueError("cache_forever cannot cache Response only its body")

        request.response.write(self.saved)
        request.response.headers.update(**self.saved_headers)
        return request.response


def synchronized(method):
    """Class method decorator to make sure two threads do not execute some code
    at the same time (c.f Java ``synchronized`` keyword).

    The decorator installs a mutex on the class instance.
    """

    @wraps(method)
    def decorated(self, *args, **kwargs):
        try:
            lock = getattr(self, "__lock__")
        except AttributeError:
            lock = threading.RLock()
            setattr(self, "__lock__", lock)

        lock.acquire()
        try:
            result = method(self, *args, **kwargs)
        finally:
            lock.release()
        return result

    return decorated


def deprecate_kwargs(deprecated):
    """
    A decorator to deprecate keyword arguments.

    :param dict deprecated: The keywords mapping (old: new)
    """

    def decorated(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            new_kwargs = {**kwargs}
            for old_param, new_param in deprecated.items():
                if old_param in kwargs:
                    message = f"{func.__qualname__} parameter {old_param!r} is deprecated, use {new_param!r} instead"
                    warnings.warn(message, DeprecationWarning)
                    new_kwargs[new_param] = new_kwargs.pop(old_param)

            return func(*args, **new_kwargs)

        return wrapper

    return decorated
