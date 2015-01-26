try:
    import simplejson as json
except ImportError:
    import json  # NOQA

import ast
from colander import null

# removes whitespace, newlines, and tabs from the beginning/end of a string
strip_whitespace = lambda v: v.strip(' \t\n\r') if v is not null else v


def native_value(value):
    """Convert string value to native python values."""
    if value.lower() in ['on', 'true', 'yes', '1']:
        value = True
    elif value.lower() in ['off', 'false', 'no', '0']:
        value = False
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def Enum(**enums):
    return type('Enum', (), enums)


COMPARISON = Enum(
    LT='<',
    MIN='>=',
    MAX='<=',
    NOT='!=',
    EQ='==',
    GT='>',
)
