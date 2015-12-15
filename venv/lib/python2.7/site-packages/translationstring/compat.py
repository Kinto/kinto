import sys

PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = (str,)
    text_type = str
else: # pragma: no cover
    string_types = (basestring,)
    text_type = unicode

if PY3: # pragma: no cover
    def u(s):
        return s
else: # pragma: no cover
    def u(s):
        return unicode(s, 'unicode_escape')

