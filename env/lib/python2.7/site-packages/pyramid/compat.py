import inspect
import platform
import sys
import types

WIN = platform.system() == 'Windows'

try:  # pragma: no cover
    import __pypy__
    PYPY = True
except:  # pragma: no cover
    __pypy__ = None
    PYPY = False

try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle

# PY3 is left as bw-compat but PY2 should be used for most checks.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    long = long
else:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    long = int

def text_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``binary_type``, return
    ``s.decode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    return s

def bytes_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``text_type``, return
    ``s.encode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

if PY2:
    def ascii_native_(s):
        if isinstance(s, text_type):
            s = s.encode('ascii')
        return str(s)
else:
    def ascii_native_(s):
        if isinstance(s, text_type):
            s = s.encode('ascii')
        return str(s, 'ascii', 'strict')

ascii_native_.__doc__ = """
Python 3: If ``s`` is an instance of ``text_type``, return
``s.encode('ascii')``, otherwise return ``str(s, 'ascii', 'strict')``

Python 2: If ``s`` is an instance of ``text_type``, return
``s.encode('ascii')``, otherwise return ``str(s)``
"""


if PY2:
    def native_(s, encoding='latin-1', errors='strict'):
        """ If ``s`` is an instance of ``text_type``, return
        ``s.encode(encoding, errors)``, otherwise return ``str(s)``"""
        if isinstance(s, text_type):
            return s.encode(encoding, errors)
        return str(s)
else:
    def native_(s, encoding='latin-1', errors='strict'):
        """ If ``s`` is an instance of ``text_type``, return
        ``s``, otherwise return ``str(s, encoding, errors)``"""
        if isinstance(s, text_type):
            return s
        return str(s, encoding, errors)

native_.__doc__ = """
Python 3: If ``s`` is an instance of ``text_type``, return ``s``, otherwise
return ``str(s, encoding, errors)``

Python 2: If ``s`` is an instance of ``text_type``, return
``s.encode(encoding, errors)``, otherwise return ``str(s)``
"""

if PY2:
    import urlparse
    from urllib import quote as url_quote
    from urllib import quote_plus as url_quote_plus
    from urllib import unquote as url_unquote
    from urllib import urlencode as url_encode
    from urllib2 import urlopen as url_open

    def url_unquote_text(v, encoding='utf-8', errors='replace'): # pragma: no cover
        v = url_unquote(v)
        return v.decode(encoding, errors)

    def url_unquote_native(v, encoding='utf-8', errors='replace'): # pragma: no cover
        return native_(url_unquote_text(v, encoding, errors))
else:
    from urllib import parse
    urlparse = parse
    from urllib.parse import quote as url_quote
    from urllib.parse import quote_plus as url_quote_plus
    from urllib.parse import unquote as url_unquote
    from urllib.parse import urlencode as url_encode
    from urllib.request import urlopen as url_open
    url_unquote_text = url_unquote
    url_unquote_native = url_unquote


if PY2:  # pragma: no cover
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

else:  # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value is None:
            value = tp
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    del builtins


if PY2:  # pragma: no cover
    def iteritems_(d):
        return d.iteritems()

    def itervalues_(d):
        return d.itervalues()

    def iterkeys_(d):
        return d.iterkeys()
else:  # pragma: no cover
    def iteritems_(d):
        return d.items()

    def itervalues_(d):
        return d.values()

    def iterkeys_(d):
        return d.keys()


if PY2:
    map_ = map
else:
    def map_(*arg):
        return list(map(*arg))

if PY2:
    def is_nonstr_iter(v):
        return hasattr(v, '__iter__')
else:
    def is_nonstr_iter(v):
        if isinstance(v, str):
            return False
        return hasattr(v, '__iter__')

if PY2:
    im_func = 'im_func'
    im_self = 'im_self'
else:
    im_func = '__func__'
    im_self = '__self__'

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

try:
    from http.cookies import SimpleCookie
except ImportError:
    from Cookie import SimpleCookie

if PY2:
    from cgi import escape
else:
    from html import escape

if PY2:
    input_ = raw_input
else:
    input_ = input

if PY2:
    from io import BytesIO as NativeIO
else:
    from io import StringIO as NativeIO

# "json" is not an API; it's here to support older pyramid_debugtoolbar
# versions which attempt to import it
import json

if PY2:
    def decode_path_info(path):
        return path.decode('utf-8')
else:
    # see PEP 3333 for why we encode WSGI PATH_INFO to latin-1 before
    # decoding it to utf-8
    def decode_path_info(path):
        return path.encode('latin-1').decode('utf-8')

if PY2:
    from urlparse import unquote as unquote_to_bytes

    def unquote_bytes_to_wsgi(bytestring):
        return unquote_to_bytes(bytestring)
else:
    # see PEP 3333 for why we decode the path to latin-1 
    from urllib.parse import unquote_to_bytes

    def unquote_bytes_to_wsgi(bytestring):
        return unquote_to_bytes(bytestring).decode('latin-1')


def is_bound_method(ob):
    return inspect.ismethod(ob) and getattr(ob, im_self, None) is not None

# support annotations and keyword-only arguments in PY3
if PY2:
    from inspect import getargspec
else:
    from inspect import getfullargspec as getargspec

if PY2:
    from itertools import izip_longest as zip_longest
else:
    from itertools import zip_longest

def is_unbound_method(fn):
    """
    This consistently verifies that the callable is bound to a
    class.
    """
    is_bound = is_bound_method(fn)

    if not is_bound and inspect.isroutine(fn):
        spec = getargspec(fn)
        has_self = len(spec.args) > 0 and spec.args[0] == 'self'

        if PY2 and inspect.ismethod(fn):
            return True
        elif inspect.isfunction(fn) and has_self:
            return True

    return False
