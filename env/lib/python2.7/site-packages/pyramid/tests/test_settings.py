import unittest

class Test_asbool(unittest.TestCase):
    def _callFUT(self, s):
        from pyramid.settings import asbool
        return asbool(s)

    def test_s_is_None(self):
        result = self._callFUT(None)
        self.assertEqual(result, False)
        
    def test_s_is_True(self):
        result = self._callFUT(True)
        self.assertEqual(result, True)
        
    def test_s_is_False(self):
        result = self._callFUT(False)
        self.assertEqual(result, False)

    def test_s_is_true(self):
        result = self._callFUT('True')
        self.assertEqual(result, True)

    def test_s_is_false(self):
        result = self._callFUT('False')
        self.assertEqual(result, False)

    def test_s_is_yes(self):
        result = self._callFUT('yes')
        self.assertEqual(result, True)

    def test_s_is_on(self):
        result = self._callFUT('on')
        self.assertEqual(result, True)

    def test_s_is_1(self):
        result = self._callFUT(1)
        self.assertEqual(result, True)

class Test_aslist_cronly(unittest.TestCase):
    def _callFUT(self, val):
        from pyramid.settings import aslist_cronly
        return aslist_cronly(val)

    def test_with_list(self):
        result = self._callFUT(['abc', 'def'])
        self.assertEqual(result, ['abc', 'def'])
        
    def test_with_string(self):
        result = self._callFUT('abc def')
        self.assertEqual(result, ['abc def'])

    def test_with_string_crsep(self):
        result = self._callFUT(' abc\n def')
        self.assertEqual(result, ['abc', 'def'])

class Test_aslist(unittest.TestCase):
    def _callFUT(self, val, **kw):
        from pyramid.settings import aslist
        return aslist(val, **kw)

    def test_with_list(self):
        result = self._callFUT(['abc', 'def'])
        self.assertEqual(list(result), ['abc', 'def'])
        
    def test_with_string(self):
        result = self._callFUT('abc def')
        self.assertEqual(result, ['abc', 'def'])

    def test_with_string_crsep(self):
        result = self._callFUT(' abc\n def')
        self.assertEqual(result, ['abc', 'def'])

    def test_with_string_crsep_spacesep(self):
        result = self._callFUT(' abc\n def ghi')
        self.assertEqual(result, ['abc', 'def', 'ghi'])

    def test_with_string_crsep_spacesep_no_flatten(self):
        result = self._callFUT(' abc\n def ghi ', flatten=False)
        self.assertEqual(result, ['abc', 'def ghi'])
