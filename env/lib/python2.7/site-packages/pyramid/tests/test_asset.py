import unittest
import os

here = os.path.abspath(os.path.dirname(__file__))

class Test_resolve_asset_spec(unittest.TestCase):
    def _callFUT(self, spec, package_name='__main__'):
        from pyramid.resource import resolve_asset_spec
        return resolve_asset_spec(spec, package_name)

    def test_abspath(self):
        package_name, filename = self._callFUT(here, 'apackage')
        self.assertEqual(filename, here)
        self.assertEqual(package_name, None)

    def test_rel_spec(self):
        pkg = 'pyramid.tests'
        path = 'test_asset.py'
        package_name, filename = self._callFUT(path, pkg)
        self.assertEqual(package_name, 'pyramid.tests')
        self.assertEqual(filename, 'test_asset.py')
        
    def test_abs_spec(self):
        pkg = 'pyramid.tests'
        path = 'pyramid.nottests:test_asset.py'
        package_name, filename = self._callFUT(path, pkg)
        self.assertEqual(package_name, 'pyramid.nottests')
        self.assertEqual(filename, 'test_asset.py')

    def test_package_name_is_None(self):
        pkg = None
        path = 'test_asset.py'
        package_name, filename = self._callFUT(path, pkg)
        self.assertEqual(package_name, None)
        self.assertEqual(filename, 'test_asset.py')

    def test_package_name_is_package_object(self):
        import pyramid.tests
        pkg = pyramid.tests
        path = 'test_asset.py'
        package_name, filename = self._callFUT(path, pkg)
        self.assertEqual(package_name, 'pyramid.tests')
        self.assertEqual(filename, 'test_asset.py')


class Test_abspath_from_asset_spec(unittest.TestCase):
    def _callFUT(self, spec, pname='__main__'):
        from pyramid.resource import abspath_from_asset_spec
        return abspath_from_asset_spec(spec, pname)

    def test_pname_is_None_before_resolve_asset_spec(self):
        result = self._callFUT('abc', None)
        self.assertEqual(result, 'abc')

    def test_pname_is_None_after_resolve_asset_spec(self):
        result = self._callFUT('/abc', '__main__')
        self.assertEqual(result, '/abc')

    def test_pkgrelative(self):
        result = self._callFUT('abc', 'pyramid.tests')
        self.assertEqual(result, os.path.join(here, 'abc'))

class Test_asset_spec_from_abspath(unittest.TestCase):
    def _callFUT(self, abspath, package):
        from pyramid.asset import asset_spec_from_abspath
        return asset_spec_from_abspath(abspath, package)

    def test_package_name_is_main(self):
        pkg = DummyPackage('__main__')
        result = self._callFUT('abspath', pkg)
        self.assertEqual(result, 'abspath')

    def test_abspath_startswith_package_path(self):
        abspath = os.path.join(here, 'fixtureapp')
        pkg = DummyPackage('pyramid.tests')
        pkg.__file__ = 'file'
        result = self._callFUT(abspath, pkg)
        self.assertEqual(result, 'pyramid:fixtureapp')

    def test_abspath_doesnt_startwith_package_path(self):
        pkg = DummyPackage('pyramid.tests')
        result = self._callFUT(here, pkg)
        self.assertEqual(result, here)

class DummyPackage:
    def __init__(self, name):
        self.__name__ = name
    
