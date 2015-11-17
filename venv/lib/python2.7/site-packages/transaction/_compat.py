import sys
import types

PY3 = sys.version_info[0] == 3
JYTHON = sys.platform.startswith('java')

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

def bytes_(s, encoding='latin-1', errors='strict'): #pragma NO COVER
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

if PY3: # pragma: no cover
    def native_(s, encoding='latin-1', errors='strict'): #pragma NO COVER
        if isinstance(s, text_type):
            return s
        return str(s, encoding, errors)
else:
    def native_(s, encoding='latin-1', errors='strict'): #pragma NO COVER
        if isinstance(s, text_type):
            return s.encode(encoding, errors)
        return str(s)

if PY3: #pragma NO COVER
    from io import StringIO
else:
    from io import BytesIO as StringIO

if PY3: #pragma NO COVER
    from collections import MutableMapping
else:
    from UserDict import UserDict as MutableMapping

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None): #pragma NO COVER
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else: # pragma: no cover
    def exec_(code, globs=None, locs=None): #pragma NO COVER
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


if PY3: #pragma NO COVER
    try:
        from threading import get_ident as get_thread_ident
    except ImportError:
        from threading import _get_ident as get_thread_ident
else:
    from thread import get_ident as get_thread_ident


if PY3:
    def func_name(func): #pragma NO COVER
        return func.__name__
else:
    def func_name(func): #pragma NO COVER
        return func.func_name
