import threading

from pyramid.registry import global_registry

class ThreadLocalManager(threading.local):
    def __init__(self, default=None):
        # http://code.google.com/p/google-app-engine-django/issues/detail?id=119
        # we *must* use a keyword argument for ``default`` here instead
        # of a positional argument to work around a bug in the
        # implementation of _threading_local.local in Python, which is
        # used by GAE instead of _thread.local
        self.stack = []
        self.default = default

    def push(self, info):
        self.stack.append(info)

    set = push # b/c

    def pop(self):
        if self.stack:
            return self.stack.pop()

    def get(self):
        try:
            return self.stack[-1]
        except IndexError:
            return self.default()

    def clear(self):
        self.stack[:] = []

def defaults():
    return {'request':None, 'registry':global_registry}

manager = ThreadLocalManager(default=defaults)

def get_current_request():
    """Return the currently active request or ``None`` if no request
    is currently active.

    This function should be used *extremely sparingly*, usually only
    in unit testing code.  It's almost always usually a mistake to use
    ``get_current_request`` outside a testing context because its
    usage makes it possible to write code that can be neither easily
    tested nor scripted.
    """
    return manager.get()['request']

def get_current_registry(context=None): # context required by getSiteManager API
    """Return the currently active :term:`application registry` or the
    global application registry if no request is currently active.

    This function should be used *extremely sparingly*, usually only
    in unit testing code.  It's almost always usually a mistake to use
    ``get_current_registry`` outside a testing context because its
    usage makes it possible to write code that can be neither easily
    tested nor scripted.
    """
    return manager.get()['registry']
