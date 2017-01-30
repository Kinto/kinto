from functools import update_wrapper


class cache_forever(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.saved = None
        update_wrapper(self, wrapped)

    def __call__(self, request, *args, **kwargs):
        if self.saved is None:
            self.saved = self.wrapped(request, *args, **kwargs)
        request.response.write(self.saved)
        return request.response
