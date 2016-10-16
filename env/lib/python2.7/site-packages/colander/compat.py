import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    string_types = basestring,
    text_type = unicode
else:
    string_types = str,
    text_type = str

def text_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``bytes``, return ``s.decode(encoding,
    errors)``, otherwise return ``s``"""
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    return s # pragma: no cover

if PY2:
    def is_nonstr_iter(v):
        return hasattr(v, '__iter__')
else:
    def is_nonstr_iter(v):
        if isinstance(v, str):
            return False
        return hasattr(v, '__iter__')

try:
    xrange = xrange
except NameError: # pragma: no cover
    xrange = range


try:
    from cPickle import loads, dumps, HIGHEST_PROTOCOL
except ImportError: # pragma: no cover
    from pickle import loads, dumps, HIGHEST_PROTOCOL
