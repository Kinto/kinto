##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import unittest

class Test_parse_http_date(unittest.TestCase):

    def _callFUT(self, v):
        from waitress.utilities import parse_http_date
        return parse_http_date(v)

    def test_rfc850(self):
        val = 'Tuesday, 08-Feb-94 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, 760716929)

    def test_rfc822(self):
        val = 'Sun, 08 Feb 1994 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, 760716929)

    def test_neither(self):
        val = ''
        result = self._callFUT(val)
        self.assertEqual(result, 0)

class Test_build_http_date(unittest.TestCase):

    def test_rountdrip(self):
        from waitress.utilities import build_http_date, parse_http_date
        from time import time
        t = int(time())
        self.assertEqual(t, parse_http_date(build_http_date(t)))

class Test_unpack_rfc850(unittest.TestCase):

    def _callFUT(self, val):
        from waitress.utilities import unpack_rfc850, rfc850_reg
        return unpack_rfc850(rfc850_reg.match(val.lower()))

    def test_it(self):
        val = 'Tuesday, 08-Feb-94 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, (1994, 2, 8, 14, 15, 29, 0, 0, 0))

class Test_unpack_rfc_822(unittest.TestCase):

    def _callFUT(self, val):
        from waitress.utilities import unpack_rfc822, rfc822_reg
        return unpack_rfc822(rfc822_reg.match(val.lower()))

    def test_it(self):
        val = 'Sun, 08 Feb 1994 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, (1994, 2, 8, 14, 15, 29, 0, 0, 0))

class Test_find_double_newline(unittest.TestCase):

    def _callFUT(self, val):
        from waitress.utilities import find_double_newline
        return find_double_newline(val)

    def test_empty(self):
        self.assertEqual(self._callFUT(b''), -1)

    def test_one_linefeed(self):
        self.assertEqual(self._callFUT(b'\n'), -1)

    def test_double_linefeed(self):
        self.assertEqual(self._callFUT(b'\n\n'), 2)

    def test_one_crlf(self):
        self.assertEqual(self._callFUT(b'\r\n'), -1)

    def test_double_crfl(self):
        self.assertEqual(self._callFUT(b'\r\n\r\n'), 4)

    def test_mixed(self):
        self.assertEqual(self._callFUT(b'\n\n00\r\n\r\n'), 2)

class Test_logging_dispatcher(unittest.TestCase):

    def _makeOne(self):
        from waitress.utilities import logging_dispatcher
        return logging_dispatcher(map={})

    def test_log_info(self):
        import logging
        inst = self._makeOne()
        logger = DummyLogger()
        inst.logger = logger
        inst.log_info('message', 'warning')
        self.assertEqual(logger.severity, logging.WARN)
        self.assertEqual(logger.message, 'message')

class TestBadRequest(unittest.TestCase):

    def _makeOne(self):
        from waitress.utilities import BadRequest
        return BadRequest(1)

    def test_it(self):
        inst = self._makeOne()
        self.assertEqual(inst.body, 1)

class DummyLogger(object):

    def log(self, severity, message):
        self.severity = severity
        self.message = message
