from six import PY3

__all__ = ['tzname_in_python2']

def tzname_in_python2(namefunc):
    """Change unicode output into bytestrings in Python 2

    tzname() API changed in Python 3. It used to return bytes, but was changed
    to unicode strings
    """
    def adjust_encoding(*args, **kwargs):
        name = namefunc(*args, **kwargs)
        if name is not None and not PY3:
            name = name.encode()

        return name

    return adjust_encoding