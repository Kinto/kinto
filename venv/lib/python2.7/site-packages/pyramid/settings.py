from pyramid.compat import string_types

truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))

def asbool(s):
    """ Return the boolean value ``True`` if the case-lowered value of string
    input ``s`` is any of ``t``, ``true``, ``y``, ``on``, or ``1``, otherwise
    return the boolean value ``False``.  If ``s`` is the value ``None``,
    return ``False``.  If ``s`` is already one of the boolean values ``True``
    or ``False``, return it."""
    if s is None:
        return False
    if isinstance(s, bool):
        return s
    s = str(s).strip()
    return s.lower() in truthy

def aslist_cronly(value):
    if isinstance(value, string_types):
        value = filter(None, [x.strip() for x in value.splitlines()])
    return list(value)

def aslist(value, flatten=True):
    """ Return a list of strings, separating the input based on newlines
    and, if flatten=True (the default), also split on spaces within
    each line."""
    values = aslist_cronly(value)
    if not flatten:
        return values
    result = []
    for value in values:
        subvalues = value.split()
        result.extend(subvalues)
    return result
