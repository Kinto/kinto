import sys
import types

try:
    import urlparse
except ImportError: # pragma: no cover
    from urllib import parse as urlparse

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    long = int
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    long = long

if PY3: # pragma: no cover
    from urllib.parse import unquote_to_bytes
    def unquote_bytes_to_wsgi(bytestring):
        return unquote_to_bytes(bytestring).decode('latin-1')
else:
    from urlparse import unquote as unquote_to_bytes
    def unquote_bytes_to_wsgi(bytestring):
        return unquote_to_bytes(bytestring)

def text_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``binary_type``, return
    ``s.decode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    return s # pragma: no cover

if PY3: # pragma: no cover
    def tostr(s):
        if isinstance(s, text_type):
            s = s.encode('latin-1')
        return str(s, 'latin-1', 'strict')

    def tobytes(s):
        return bytes(s, 'latin-1')
else:
    tostr = str

    def tobytes(s):
        return s

try:
    from Queue import (
        Queue,
        Empty,
    )
except ImportError: # pragma: no cover
    from queue import (
        Queue,
        Empty,
    )

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value is None:
            value = tp
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    del builtins

else: # pragma: no cover
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

try:
    from StringIO import StringIO as NativeIO
except ImportError: # pragma: no cover
    from io import StringIO as NativeIO

try:
    import httplib
except ImportError: # pragma: no cover
    from http import client as httplib

try:
    MAXINT = sys.maxint
except AttributeError: # pragma: no cover
    MAXINT = sys.maxsize
