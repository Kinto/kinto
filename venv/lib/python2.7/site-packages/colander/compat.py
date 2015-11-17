import sys

PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = str,
    text_type = str
else: # pragma: no cover
    string_types = basestring,
    text_type = unicode

def text_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``bytes``, return ``s.decode(encoding,
    errors)``, otherwise return ``s``"""
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    return s # pragma: no cover

if PY3: # pragma: no cover
    def is_nonstr_iter(v):
        if isinstance(v, str):
            return False
        return hasattr(v, '__iter__')
else: # pragma: no cover
    def is_nonstr_iter(v):
        return hasattr(v, '__iter__')

try:
    xrange = xrange
except NameError: # pragma: no cover
    xrange = range


try:
    from cPickle import loads, dumps, HIGHEST_PROTOCOL
except ImportError: # pragma: no cover
    from pickle import loads, dumps, HIGHEST_PROTOCOL
