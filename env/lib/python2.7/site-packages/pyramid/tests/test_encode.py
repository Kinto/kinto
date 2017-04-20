import unittest
from pyramid.compat import (
    text_,
    native_,
    )

class UrlEncodeTests(unittest.TestCase):
    def _callFUT(self, query, doseq=False):
        from pyramid.encode import urlencode
        return urlencode(query, doseq)

    def test_ascii_only(self):
        result = self._callFUT([('a',1), ('b',2)])
        self.assertEqual(result, 'a=1&b=2')

    def test_unicode_key(self):
        la = text_(b'LaPe\xc3\xb1a', 'utf-8')
        result = self._callFUT([(la, 1), ('b',2)])
        self.assertEqual(result, 'LaPe%C3%B1a=1&b=2')

    def test_unicode_val_single(self):
        la = text_(b'LaPe\xc3\xb1a', 'utf-8')
        result = self._callFUT([('a', la), ('b',2)])
        self.assertEqual(result, 'a=LaPe%C3%B1a&b=2')

    def test_unicode_val_multiple(self):
        la = [text_(b'LaPe\xc3\xb1a', 'utf-8')] * 2
        result = self._callFUT([('a', la), ('b',2)], doseq=True)
        self.assertEqual(result, 'a=LaPe%C3%B1a&a=LaPe%C3%B1a&b=2')

    def test_int_val_multiple(self):
        s = [1, 2]
        result = self._callFUT([('a', s)], doseq=True)
        self.assertEqual(result, 'a=1&a=2')

    def test_with_spaces(self):
        result = self._callFUT([('a', '123 456')], doseq=True)
        self.assertEqual(result, 'a=123+456')

    def test_dict(self):
        result = self._callFUT({'a':1})
        self.assertEqual(result, 'a=1')

    def test_None_value(self):
        result = self._callFUT([('a', None)])
        self.assertEqual(result, 'a=')

    def test_None_value_with_prefix(self):
        result = self._callFUT([('a', '1'), ('b', None)])
        self.assertEqual(result, 'a=1&b=')

    def test_None_value_with_prefix_values(self):
        result = self._callFUT([('a', '1'), ('b', None), ('c', None)])
        self.assertEqual(result, 'a=1&b=&c=')

class URLQuoteTests(unittest.TestCase):
    def _callFUT(self, val, safe=''):
        from pyramid.encode import url_quote
        return url_quote(val, safe)

    def test_it_bytes(self):
        la = b'La/Pe\xc3\xb1a'
        result = self._callFUT(la)
        self.assertEqual(result, 'La%2FPe%C3%B1a')
        
    def test_it_native(self):
        la = native_(b'La/Pe\xc3\xb1a', 'utf-8')
        result = self._callFUT(la)
        self.assertEqual(result, 'La%2FPe%C3%B1a')

    def test_it_with_safe(self):
        la = b'La/Pe\xc3\xb1a'
        result = self._callFUT(la, '/')
        self.assertEqual(result, 'La/Pe%C3%B1a')

    def test_it_with_nonstr_nonbinary(self):
        la = None
        result = self._callFUT(la, '/')
        self.assertEqual(result, 'None')
