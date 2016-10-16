import unittest
import datetime

class Test_Utc(unittest.TestCase):
    def _makeOne(self):
        from ..iso8601 import Utc
        return Utc()

    def test_utcoffset(self):
        from ..iso8601 import ZERO
        inst = self._makeOne()
        result = inst.utcoffset(None)
        self.assertEqual(result, ZERO)

    def test_tzname(self):
        inst = self._makeOne()
        result = inst.tzname(None)
        self.assertEqual(result, "UTC")

    def test_dst(self):
        from ..iso8601 import ZERO
        inst = self._makeOne()
        result = inst.dst(None)
        self.assertEqual(result, ZERO)

    def test_picklability(self):
        from ..iso8601 import ZERO
        from ..compat import loads, dumps, HIGHEST_PROTOCOL
        inst = self._makeOne()
        for protocol in range(HIGHEST_PROTOCOL + 1):
            inst2 = loads(dumps(inst, protocol))
            self.assertEqual(inst2.utcoffset(None), ZERO)
            self.assertEqual(inst2.tzname(None), 'UTC')
            self.assertEqual(inst2.dst(None), ZERO)

class Test_FixedOffset(unittest.TestCase):
    def _makeOne(self):
        from ..iso8601 import FixedOffset
        return FixedOffset(1, 30, 'oneandahalf')

    def test_utcoffset(self):
        inst = self._makeOne()
        result = inst.utcoffset(None)
        self.assertEqual(result, datetime.timedelta(hours=1, minutes=30))

    def test_tzname(self):
        inst = self._makeOne()
        result = inst.tzname(None)
        self.assertEqual(result, 'oneandahalf')

    def test_dst(self):
        from ..iso8601 import ZERO
        inst = self._makeOne()
        result = inst.dst(None)
        self.assertEqual(result, ZERO)

    def test_picklability(self):
        from ..iso8601 import ZERO
        from ..compat import loads, dumps, HIGHEST_PROTOCOL
        inst = self._makeOne()
        for protocol in range(HIGHEST_PROTOCOL + 1):
            inst2 = loads(dumps(inst, protocol))
            self.assertEqual(inst2.utcoffset(None),
                            datetime.timedelta(hours=1, minutes=30))
            self.assertEqual(inst2.tzname(None), 'oneandahalf')
            self.assertEqual(inst2.dst(None), ZERO)

    def test___repr__(self):
        inst = self._makeOne()
        result = inst.__repr__()
        self.assertEqual(result, "<FixedOffset 'oneandahalf' datetime.timedelta(0, 5400)>")

class Test_parse_timezone(unittest.TestCase):
    def _callFUT(self, tzstring, **kw):
        # mimic old parse_timezone() by returning a FixedOffset
        from datetime import tzinfo
        from ..iso8601 import (parse_date, FixedOffset)
        if tzstring is None:
            tzstring = ''
        dt = parse_date("2006-10-11T00:14:33{0}".format(tzstring), **kw)
        return dt.tzinfo

    def test_default_Z(self):
        from ..iso8601 import UTC
        result = self._callFUT('Z')
        self.assertEqual(result, UTC)

    def test_Z_with_default_timezone(self):
        from ..iso8601 import UTC, FixedOffset
        tz = FixedOffset(1, 0, 'myname')
        result = self._callFUT('Z', default_timezone=tz)
        self.assertEqual(result, UTC)

    def test_default_None(self):
        from ..iso8601 import UTC
        result = self._callFUT(None)
        self.assertEqual(result, UTC)

    def test_None_with_default_timezone(self):
        from ..iso8601 import FixedOffset
        tz = FixedOffset(1, 0, 'myname')
        result = self._callFUT(None, default_timezone=tz)
        self.assertEqual(result, tz)

    def test_positive(self):
        tzstring = "+01:00"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None),
                         datetime.timedelta(hours=1, minutes=0))

    def test_positive_without_colon(self):
        tzstring = "+0100"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None),
                         datetime.timedelta(hours=1, minutes=0))

    def test_positive_without_minutes(self):
        tzstring = "+01"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None),
                         datetime.timedelta(hours=1, minutes=0))

    def test_negative(self):
        tzstring = "-01:00"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None),
                         datetime.timedelta(hours=-1, minutes=0))

    def test_negative_without_colon(self):
        tzstring = "-0100"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None),
                         datetime.timedelta(hours=-1, minutes=0))

    def test_negative_without_minutes(self):
        tzstring = "-01"
        result = self._callFUT(tzstring)
        self.assertEqual(result.utcoffset(None),
                         datetime.timedelta(hours=-1, minutes=0))

class Test_parse_date(unittest.TestCase):
    def _callFUT(self, datestring):
        from ..iso8601 import parse_date
        return parse_date(datestring)

    def test_notastring(self):
        from ..iso8601 import ParseError
        self.assertRaises(ParseError, self._callFUT, None)

    def test_cantparse(self):
        from ..iso8601 import ParseError
        self.assertRaises(ParseError, self._callFUT, 'garbage')

    def test_outfrange(self):
        from ..iso8601 import ParseError
        self.assertRaises(ParseError, self._callFUT, '2013-05-32')

    def test_normal(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25T12:00:00Z")
        self.assertEqual(result,
                         datetime.datetime(2007, 1, 25, 12, 0, tzinfo=UTC))

    def test_fraction(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25T12:00:00.123Z")
        self.assertEqual(result,
                         datetime.datetime(2007, 1, 25, 12, 0, 0, 123000,
                                           tzinfo=UTC))

    def test_no_seconds(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25T12:00Z")
        self.assertEqual(result,
                         datetime.datetime(2007, 1, 25, 12, 0, 0, 0,
                                           tzinfo=UTC))

    def test_no_minutes(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25T12Z")
        self.assertEqual(result,
                         datetime.datetime(2007, 1, 25, 12, 0, 0, 0,
                                           tzinfo=UTC))

    def test_no_hours(self):
        from ..iso8601 import UTC
        result = self._callFUT("2007-01-25")
        self.assertEqual(result,
                         datetime.datetime(2007, 1, 25, 0, 0, 0, 0,
                                           tzinfo=UTC))

    def test_slash_separated_raises_ParseError(self):
        from ..iso8601 import ParseError
        self.assertRaises(ParseError, self._callFUT, "2007/01/25")

