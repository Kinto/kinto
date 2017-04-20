import unittest

class TestBWCompat(unittest.TestCase):
    def test_bwcompat_notfound(self):
        from pyramid.exceptions import NotFound as one
        from pyramid.httpexceptions import HTTPNotFound as two
        self.assertTrue(one is two)

    def test_bwcompat_forbidden(self):
        from pyramid.exceptions import Forbidden as one
        from pyramid.httpexceptions import HTTPForbidden as two
        self.assertTrue(one is two)

class TestBadCSRFToken(unittest.TestCase):
    def test_response_equivalence(self):
        from pyramid.exceptions import BadCSRFToken
        from pyramid.httpexceptions import HTTPBadRequest
        self.assertTrue(isinstance(BadCSRFToken(), HTTPBadRequest))

class TestNotFound(unittest.TestCase):
    def _makeOne(self, message):
        from pyramid.exceptions import NotFound
        return NotFound(message)

    def test_it(self):
        from pyramid.interfaces import IExceptionResponse
        e = self._makeOne('notfound')
        self.assertTrue(IExceptionResponse.providedBy(e))
        self.assertEqual(e.status, '404 Not Found')
        self.assertEqual(e.message, 'notfound')

    def test_response_equivalence(self):
        from pyramid.exceptions import NotFound
        from pyramid.httpexceptions import HTTPNotFound
        self.assertTrue(NotFound is HTTPNotFound)

class TestForbidden(unittest.TestCase):
    def _makeOne(self, message):
        from pyramid.exceptions import Forbidden
        return Forbidden(message)

    def test_it(self):
        from pyramid.interfaces import IExceptionResponse
        e = self._makeOne('forbidden')
        self.assertTrue(IExceptionResponse.providedBy(e))
        self.assertEqual(e.status, '403 Forbidden')
        self.assertEqual(e.message, 'forbidden')

    def test_response_equivalence(self):
        from pyramid.exceptions import Forbidden
        from pyramid.httpexceptions import HTTPForbidden
        self.assertTrue(Forbidden is HTTPForbidden)

class TestConfigurationConflictError(unittest.TestCase):
    def _makeOne(self, conflicts):
        from pyramid.exceptions import ConfigurationConflictError
        return ConfigurationConflictError(conflicts)

    def test_str(self):
        conflicts = {'a':('1', '2', '3'), 'b':('4', '5', '6')}
        exc = self._makeOne(conflicts)
        self.assertEqual(str(exc),
"""\
Conflicting configuration actions
  For: a
    1
    2
    3
  For: b
    4
    5
    6""")

class TestConfigurationExecutionError(unittest.TestCase):
    def _makeOne(self, etype, evalue, info):
        from pyramid.exceptions import ConfigurationExecutionError
        return ConfigurationExecutionError(etype, evalue, info)

    def test_str(self):
        exc = self._makeOne('etype', 'evalue', 'info')
        self.assertEqual(str(exc), 'etype: evalue\n  in:\n  info')
        
class TestCyclicDependencyError(unittest.TestCase):
    def _makeOne(self, cycles):
        from pyramid.exceptions import CyclicDependencyError
        return CyclicDependencyError(cycles)

    def test___str__(self):
        exc = self._makeOne({'a':['c', 'd'], 'c':['a']})
        result = str(exc)
        self.assertTrue("'a' sorts before ['c', 'd']" in result)
        self.assertTrue("'c' sorts before ['a']" in result)


