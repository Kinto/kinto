try:
    import simplejson as json
except ImportError:  # pragma: no cover
    import json  # NOQA

import ast
import time

from colander import null


# removes whitespace, newlines, and tabs from the beginning/end of a string
strip_whitespace = lambda v: v.strip(' \t\n\r') if v is not null else v

time_second = lambda: int(time.time())
msec_time = lambda: int(time.time() * 1000.0)  # floor


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
