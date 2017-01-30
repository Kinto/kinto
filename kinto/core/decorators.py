from functools import update_wrapper
from pyramid.response import Response


class cache_forever(object):
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
