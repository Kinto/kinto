try:
    import simplejson as json
except ImportError:  # pragma: no cover
    import json  # NOQA

import ast
import decimal
import threading
import time

from colander import null


# removes whitespace, newlines, and tabs from the beginning/end of a string
strip_whitespace = lambda v: v.strip(' \t\n\r') if v is not null else v

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


class TimeStamper(object):
    """A helper to generate accurate timestamps.

    It increments a fraction in case prevent two simultaneous calls to return
    the same timestamp.

    This is mainly used for in-memory backend. Ideally, this task should rely
    on storage backend transaction capabilities to guarantee timestamp unicity
    in a multiprocess environment.

    .. note:

        Original comes from http://stackoverflow.com/a/157711
    """
    fraction = decimal.Decimal('0.001')

    def __init__(self):
        self.lock = threading.Lock()
        self.prev = None
        self.count = 0

    def now(self):
        with self.lock:
            timestamp = decimal.Decimal(msec_time())
            if timestamp == self.prev:
                timestamp += self.count * self.fraction
                self.count += 1
            else:
                self.prev = timestamp
                self.count = 1
            return timestamp


timestamper = TimeStamper()
