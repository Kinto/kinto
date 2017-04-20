# -*- coding: utf-8 -*-

import unittest

class Test_unquote_bytes_to_wsgi(unittest.TestCase):

    def _callFUT(self, v):
        from waitress.compat import unquote_bytes_to_wsgi
        return unquote_bytes_to_wsgi(v)

    def test_highorder(self):
        from waitress.compat import PY3
        val = b'/a%C5%9B'
        result = self._callFUT(val)
        if PY3: # pragma: no cover
            # PEP 3333 urlunquoted-latin1-decoded-bytes
            self.assertEqual(result, '/aÅ\x9b')
        else: # pragma: no cover
            # sanity
            self.assertEqual(result, b'/a\xc5\x9b')
