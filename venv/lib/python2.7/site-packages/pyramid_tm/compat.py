import sys

PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    text_type = str
    binary_type = bytes

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    def native_(s, encoding='latin-1', errors='strict'):
        if isinstance(s, text_type):
            return s
        if isinstance(s, binary_type):
            return str(s, encoding, errors)
        return str(s)

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

    text_type = unicode
    binary_type = str

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

    def native_(s, encoding='latin-1', errors='strict'):
        if isinstance(s, text_type):
            return s.encode(encoding, errors)
        return str(s)
