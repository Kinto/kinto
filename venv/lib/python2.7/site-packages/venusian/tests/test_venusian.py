import unittest
import sys
import re

class Test(object):
    def __init__(self):
        self.registrations = []
    def __call__(self, **kw):
        self.registrations.append(kw)

class TestScanner(unittest.TestCase):
    def _makeOne(self, **kw):
        from venusian import Scanner
        return Scanner(**kw)

    def test_package(self):
        from venusian.tests.fixtures import one
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(one)
        self.assertEqual(len(test.registrations), 6)
        test.registrations.sort(key=lambda x: (x['name'], x['ob'].__module__))
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module2 import function as func2
        from venusian.tests.fixtures.one.module import inst as inst1
        from venusian.tests.fixtures.one.module2 import inst as inst2
        from venusian.tests.fixtures.one.module import Class as Class1
        from venusian.tests.fixtures.one.module2 import Class as Class2

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'Class')
        self.assertEqual(test.registrations[1]['ob'], Class2)
        self.assertEqual(test.registrations[1]['method'], True)

        self.assertEqual(test.registrations[2]['name'], 'function')
        self.assertEqual(test.registrations[2]['ob'], func1)
        self.assertEqual(test.registrations[2]['function'], True)

        self.assertEqual(test.registrations[3]['name'], 'function')
        self.assertEqual(test.registrations[3]['ob'], func2)
        self.assertEqual(test.registrations[3]['function'], True)
        
        self.assertEqual(test.registrations[4]['name'], 'inst')
        self.assertEqual(test.registrations[4]['ob'], inst1)
        self.assertEqual(test.registrations[4]['instance'], True)

        self.assertEqual(test.registrations[5]['name'], 'inst')
        self.assertEqual(test.registrations[5]['ob'], inst2)
        self.assertEqual(test.registrations[5]['instance'], True)

    def test_package_with_orphaned_pyc_file(self):
        # There is a module2.pyc file in the "pycfixtures" package; it
        # has no corresponding .py source file.  Such orphaned .pyc
        # files should be ignored during scanning.
        from venusian.tests.fixtures import pyc
        test = Test()
        scanner = self._makeOne(test=test) 
        scanner.scan(pyc)
        self.assertEqual(len(test.registrations), 4)
        test.registrations.sort(key=lambda x: (x['name'], x['ob'].__module__))
        from venusian.tests.fixtures.pyc.module import function as func1
        from venusian.tests.fixtures.pyc.module import inst as inst1
        from venusian.tests.fixtures.pyc.module import Class as Class1
        from venusian.tests.fixtures.pyc import subpackage

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func1)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'inst')
        self.assertEqual(test.registrations[2]['ob'], inst1)
        self.assertEqual(test.registrations[2]['instance'], True)

        self.assertEqual(test.registrations[3]['name'], 'pkgfunction')
        self.assertEqual(test.registrations[3]['ob'], subpackage.pkgfunction)
        self.assertEqual(test.registrations[3]['function'], True)

    def test_module(self):
        from venusian.tests.fixtures.one import module
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(module)
        self.assertEqual(len(test.registrations), 3)
        test.registrations.sort(key=lambda x: (x['name'], x['ob'].__module__))
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module import inst as inst1
        from venusian.tests.fixtures.one.module import Class as Class1

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func1)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'inst')
        self.assertEqual(test.registrations[2]['ob'], inst1)
        self.assertEqual(test.registrations[2]['instance'], True)

    def test_ignore_imported(self):
        # even though "twofunction" is imported into "one", it should not
        # be registered, because it's only imported in one and not defined
        # there
        from venusian.tests.fixtures.importonly import one
        from venusian.tests.fixtures.importonly import two
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(one)
        self.assertEqual(len(test.registrations), 1)
        scanner.scan(two)
        self.assertEqual(len(test.registrations), 2)

    def test_dont_ignore_legit_decorators(self):
        # make sure venusian picks up other decorated things from
        # imported modules when the whole package is scanned
        from venusian.tests.fixtures import import_and_scan
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(import_and_scan)
        self.assertEqual(len(test.registrations), 2)

    def test_one_category(self):
        from venusian.tests.fixtures import category
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(category, categories=('mycategory',))
        self.assertEqual(len(test.registrations), 1)
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], category.function)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_all_categories_implicit(self):
        from venusian.tests.fixtures import category
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(category)
        self.assertEqual(len(test.registrations), 2)
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], category.function)
        self.assertEqual(test.registrations[0]['function'], True)
        self.assertEqual(test.registrations[1]['name'], 'function2')
        self.assertEqual(test.registrations[1]['ob'], category.function2)
        self.assertEqual(test.registrations[1]['function'], True)

    def test_all_categories_explicit(self):
        from venusian.tests.fixtures import category
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(category, categories=('mycategory', 'mycategory2'))
        self.assertEqual(len(test.registrations), 2)
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], category.function)
        self.assertEqual(test.registrations[0]['function'], True)
        self.assertEqual(test.registrations[1]['name'], 'function2')
        self.assertEqual(test.registrations[1]['ob'], category.function2)
        self.assertEqual(test.registrations[1]['function'], True)

    if sys.version_info >= (2, 6):

        def test_decorations_arent_inherited(self):
            from venusian.tests.fixtures import inheritance
            test = Test()
            scanner = self._makeOne(test=test)
            scanner.scan(inheritance)
            self.assertEqual(test.registrations, [
                dict(name='Parent',
                     ob=inheritance.Parent),
                ])

        def test_classdecorator(self): # pragma: no cover
            from venusian.tests.fixtures import classdecorator
            test = Test()
            scanner = self._makeOne(test=test)
            scanner.scan(classdecorator)
            test.registrations.sort(key=lambda x: (x['name'], x['ob'].__module__))
            self.assertEqual(len(test.registrations), 2)
            self.assertEqual(test.registrations[0]['name'], 'SubClass')
            self.assertEqual(test.registrations[0]['ob'],
                             classdecorator.SubClass)
            self.assertEqual(test.registrations[0]['subclass'], True)
            self.assertEqual(test.registrations[1]['name'], 'SuperClass')
            self.assertEqual(test.registrations[1]['ob'],
                             classdecorator.SuperClass)
            self.assertEqual(test.registrations[1]['superclass'], True)

        def test_scan_only_finds_classdecoration_once(self):
            from venusian.tests.fixtures import two
            from venusian.tests.fixtures.two.mod1 import Class
            test = Test()
            scanner = self._makeOne(test=test)
            scanner.scan(two)
            self.assertEqual(test.registrations, [
                dict(name='Class',
                     ob=Class),
                ])
            
    def test_importerror_during_scan_default_onerror(self):
        from venusian.tests.fixtures import importerror
        test = Test()
        scanner = self._makeOne(test=test)
        # without a custom onerror, scan will propagate the importerror from
        # will_cause_import_error
        self.assertRaises(ImportError, scanner.scan, importerror)

    def test_importerror_during_scan_default_onerror_with_ignore(self):
        from venusian.tests.fixtures import importerror
        test = Test()
        scanner = self._makeOne(test=test)
        # scan will ignore the errors from will_cause_import_error due
        # to us choosing to ignore that package
        scanner.scan(
            importerror,
            ignore='venusian.tests.fixtures.importerror.will_cause_import_error')

    def test_importerror_during_scan_custom_onerror(self):
        from venusian.tests.fixtures import importerror
        test = Test()
        scanner = self._makeOne(test=test)
        # with this custom onerror, scan will not propagate the importerror
        # from will_raise_importerror
        def onerror(name):
            if not issubclass(sys.exc_info()[0], ImportError): raise
        scanner.scan(importerror, onerror=onerror)
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.importerror import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_importerror_in_package_during_scan_custom_onerror(self):
        from venusian.tests.fixtures import importerror_package
        md('venusian.tests.fixtures.importerror_package.will_cause_import_error')
        test = Test()
        scanner = self._makeOne(test=test)
        # with this custom onerror, scan will not propagate the importerror
        # from will_raise_importerror
        def onerror(name):
            raise ValueError
        self.assertRaises(ValueError, scanner.scan, importerror_package,
                          onerror=onerror)
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.importerror_package import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_attrerror_during_scan_custom_onerror(self):
        from venusian.tests.fixtures import attrerror
        test = Test()
        scanner = self._makeOne(test=test)
        # with this custom onerror, scan will not propagate the importerror
        # from will_raise_importerror
        def onerror(name):
            if not issubclass(sys.exc_info()[0], ImportError): raise
        self.assertRaises(AttributeError, scanner.scan, attrerror,
                          onerror=onerror)
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.attrerror import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_attrerror_in_package_during_scan_custom_onerror(self):
        from venusian.tests.fixtures import attrerror_package
        md('venusian.tests.fixtures.attrerror_package.will_cause_import_error')
        test = Test()
        scanner = self._makeOne(test=test)
        # with this custom onerror, scan will not propagate the importerror
        # from will_raise_importerror
        def onerror(name):
            if not issubclass(sys.exc_info()[0], ImportError): raise
        self.assertRaises(AttributeError, scanner.scan, attrerror_package,
                          onerror=onerror)
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.attrerror_package import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)
        
    def test_attrerror_in_package_during_scan_no_custom_onerror(self):
        from venusian.tests.fixtures import attrerror_package
        md('venusian.tests.fixtures.attrerror_package.will_cause_import_error')
        test = Test()
        scanner = self._makeOne(test=test)
        self.assertRaises(AttributeError, scanner.scan, attrerror_package)
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.attrerror_package import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)
        
    def test_onerror_used_to_swallow_all_exceptions(self):
        from venusian.tests.fixtures import subpackages
        test = Test()
        scanner = self._makeOne(test=test)
        # onerror can also be used to skip errors while scanning submodules
        # e.g.: test modules under a given library
        swallowed = []
        def ignore_child(name):
            swallowed.append(name)
        scanner.scan(subpackages, onerror=ignore_child)
        self.assertEqual(swallowed,
          ['venusian.tests.fixtures.subpackages.childpackage.will_cause_import_error',
           'venusian.tests.fixtures.subpackages.mod2'])
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.subpackages import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_ignore_by_full_dotted_name(self):
        from venusian.tests.fixtures import one
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            one, 
            ignore=['venusian.tests.fixtures.one.module2']
            )
        self.assertEqual(len(test.registrations), 3)
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module import inst as inst1
        from venusian.tests.fixtures.one.module import Class as Class1

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func1)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'inst')
        self.assertEqual(test.registrations[2]['ob'], inst1)
        self.assertEqual(test.registrations[2]['instance'], True)

    def test_ignore_by_full_dotted_name2(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=['venusian.tests.fixtures.nested.sub1']
            )
        self.assertEqual(len(test.registrations), 3)
        from venusian.tests.fixtures.nested import function as func1
        from venusian.tests.fixtures.nested.sub2 import function as func2
        from venusian.tests.fixtures.nested.sub2.subsub2 import function as func3

        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func2)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'function')
        self.assertEqual(test.registrations[2]['ob'], func3)
        self.assertEqual(test.registrations[2]['function'], True)

    def test_ignore_by_full_dotted_name3(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=['venusian.tests.fixtures.nested.sub1',
                    'venusian.tests.fixtures.nested.sub2']
            )
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.nested import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_ignore_by_full_dotted_name4(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=['venusian.tests.fixtures.nested.sub1',
                    'venusian.tests.fixtures.nested.function']
            )
        self.assertEqual(len(test.registrations), 2)
        from venusian.tests.fixtures.nested.sub2 import function as func2
        from venusian.tests.fixtures.nested.sub2.subsub2 import function as func3

        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func2)
        self.assertEqual(test.registrations[0]['function'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func3)
        self.assertEqual(test.registrations[1]['function'], True)

    def test_ignore_by_relative_dotted_name(self):
        from venusian.tests.fixtures import one
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(one,  ignore=['.module2'])
        self.assertEqual(len(test.registrations), 3)
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module import inst as inst1
        from venusian.tests.fixtures.one.module import Class as Class1

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func1)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'inst')
        self.assertEqual(test.registrations[2]['ob'], inst1)
        self.assertEqual(test.registrations[2]['instance'], True)
        
    def test_ignore_by_relative_dotted_name2(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=['.sub1']
            )
        self.assertEqual(len(test.registrations), 3)
        from venusian.tests.fixtures.nested import function as func1
        from venusian.tests.fixtures.nested.sub2 import function as func2
        from venusian.tests.fixtures.nested.sub2.subsub2 import function as func3

        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func2)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'function')
        self.assertEqual(test.registrations[2]['ob'], func3)
        self.assertEqual(test.registrations[2]['function'], True)

    def test_ignore_by_relative_dotted_name3(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=['.sub1', '.sub2']
            )
        self.assertEqual(len(test.registrations), 1)
        from venusian.tests.fixtures.nested import function as func1
        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

    def test_ignore_by_relative_dotted_name4(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=['.sub1', '.function']
            )
        self.assertEqual(len(test.registrations), 2)
        from venusian.tests.fixtures.nested.sub2 import function as func2
        from venusian.tests.fixtures.nested.sub2.subsub2 import function as func3

        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func2)
        self.assertEqual(test.registrations[0]['function'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func3)
        self.assertEqual(test.registrations[1]['function'], True)

    def test_ignore_by_function(self):
        from venusian.tests.fixtures import one
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(one, ignore=[re.compile('Class').search, 
                                  re.compile('inst').search])
        self.assertEqual(len(test.registrations), 2)
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module2 import function as func2

        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func1)
        self.assertEqual(test.registrations[0]['function'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func2)
        self.assertEqual(test.registrations[1]['function'], True)

    def test_ignore_by_function_nested(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=[re.compile('.function$').search]
            )
        self.assertEqual(len(test.registrations), 0)

    def test_ignore_by_function_nested2(self):
        from venusian.tests.fixtures import nested
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(
            nested, 
            ignore=[re.compile('sub2$').search,
                    re.compile('nested.function$').search]
            )
        self.assertEqual(len(test.registrations), 2)

        from venusian.tests.fixtures.nested.sub1 import function as func2
        from venusian.tests.fixtures.nested.sub1.subsub1 import function as func3

        self.assertEqual(test.registrations[0]['name'], 'function')
        self.assertEqual(test.registrations[0]['ob'], func2)
        self.assertEqual(test.registrations[0]['function'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func3)
        self.assertEqual(test.registrations[1]['function'], True)
        
        
    def test_ignore_as_string(self):
        from venusian.tests.fixtures import one
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(one, ignore='venusian.tests.fixtures.one.module2')
        self.assertEqual(len(test.registrations), 3)
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module import inst as inst1
        from venusian.tests.fixtures.one.module import Class as Class1

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func1)
        self.assertEqual(test.registrations[1]['function'], True)

        self.assertEqual(test.registrations[2]['name'], 'inst')
        self.assertEqual(test.registrations[2]['ob'], inst1)
        self.assertEqual(test.registrations[2]['instance'], True)
        
    def test_ignore_mixed_string_and_func(self):
        import re
        from venusian.tests.fixtures import one
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(one, ignore=['venusian.tests.fixtures.one.module2',
                                  re.compile('inst').search])
        self.assertEqual(len(test.registrations), 2)
        from venusian.tests.fixtures.one.module import function as func1
        from venusian.tests.fixtures.one.module import Class as Class1

        self.assertEqual(test.registrations[0]['name'], 'Class')
        self.assertEqual(test.registrations[0]['ob'], Class1)
        self.assertEqual(test.registrations[0]['method'], True)

        self.assertEqual(test.registrations[1]['name'], 'function')
        self.assertEqual(test.registrations[1]['ob'], func1)
        self.assertEqual(test.registrations[1]['function'], True)

    def test_lifting1(self):
        from venusian.tests.fixtures import lifting1
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(lifting1)
        test.registrations.sort(
            key=lambda x: (x['name'], x['attr'], x['ob'].__module__)
            )
        self.assertEqual(len(test.registrations), 11)

        self.assertEqual(test.registrations[0]['attr'], 'boo')
        self.assertEqual(test.registrations[0]['name'], 'Sub')
        self.assertEqual(test.registrations[0]['ob'], lifting1.Sub)

        self.assertEqual(test.registrations[1]['attr'], 'classname')
        self.assertEqual(test.registrations[1]['name'], 'Sub')
        self.assertEqual(test.registrations[1]['ob'], lifting1.Sub)

        self.assertEqual(test.registrations[2]['attr'], 'hiss')
        self.assertEqual(test.registrations[2]['name'], 'Sub')
        self.assertEqual(test.registrations[2]['ob'], lifting1.Sub)

        self.assertEqual(test.registrations[3]['attr'], 'jump')
        self.assertEqual(test.registrations[3]['name'], 'Sub')
        self.assertEqual(test.registrations[3]['ob'], lifting1.Sub)

        self.assertEqual(test.registrations[4]['attr'], 'ram')
        self.assertEqual(test.registrations[4]['name'], 'Sub')
        self.assertEqual(test.registrations[4]['ob'], lifting1.Sub)

        self.assertEqual(test.registrations[5]['attr'], 'smack')
        self.assertEqual(test.registrations[5]['name'], 'Sub')
        self.assertEqual(test.registrations[5]['ob'], lifting1.Sub)

        self.assertEqual(test.registrations[6]['attr'], 'boo')
        self.assertEqual(test.registrations[6]['name'], 'Super1')
        self.assertEqual(test.registrations[6]['ob'], lifting1.Super1)

        self.assertEqual(test.registrations[7]['attr'], 'classname')
        self.assertEqual(test.registrations[7]['name'], 'Super1')
        self.assertEqual(test.registrations[7]['ob'], lifting1.Super1)

        self.assertEqual(test.registrations[8]['attr'], 'ram')
        self.assertEqual(test.registrations[8]['name'], 'Super1')
        self.assertEqual(test.registrations[8]['ob'], lifting1.Super1)

        self.assertEqual(test.registrations[9]['attr'], 'hiss')
        self.assertEqual(test.registrations[9]['name'], 'Super2')
        self.assertEqual(test.registrations[9]['ob'], lifting1.Super2)

        self.assertEqual(test.registrations[10]['attr'], 'jump')
        self.assertEqual(test.registrations[10]['name'], 'Super2')
        self.assertEqual(test.registrations[10]['ob'], lifting1.Super2)

    def test_lifting2(self):
        from venusian.tests.fixtures import lifting2
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(lifting2)
        test.registrations.sort(
            key=lambda x: (x['name'], x['attr'], x['ob'].__module__)
            )
        self.assertEqual(len(test.registrations), 6)

        self.assertEqual(test.registrations[0]['attr'], 'boo')
        self.assertEqual(test.registrations[0]['name'], 'Sub')
        self.assertEqual(test.registrations[0]['ob'], lifting2.Sub)

        self.assertEqual(test.registrations[1]['attr'], 'classname')
        self.assertEqual(test.registrations[1]['name'], 'Sub')
        self.assertEqual(test.registrations[1]['ob'], lifting2.Sub)

        self.assertEqual(test.registrations[2]['attr'], 'hiss')
        self.assertEqual(test.registrations[2]['name'], 'Sub')
        self.assertEqual(test.registrations[2]['ob'], lifting2.Sub)

        self.assertEqual(test.registrations[3]['attr'], 'jump')
        self.assertEqual(test.registrations[3]['name'], 'Sub')
        self.assertEqual(test.registrations[3]['ob'], lifting2.Sub)

        self.assertEqual(test.registrations[4]['attr'], 'ram')
        self.assertEqual(test.registrations[4]['name'], 'Sub')
        self.assertEqual(test.registrations[4]['ob'], lifting2.Sub)

        self.assertEqual(test.registrations[5]['attr'], 'smack')
        self.assertEqual(test.registrations[5]['name'], 'Sub')
        self.assertEqual(test.registrations[5]['ob'], lifting2.Sub)

    def test_lifting3(self):
        from venusian.tests.fixtures import lifting3
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(lifting3)
        test.registrations.sort(
            key=lambda x: (x['name'], x['attr'], x['ob'].__module__)
            )
        self.assertEqual(len(test.registrations), 8)

        self.assertEqual(test.registrations[0]['attr'], 'boo')
        self.assertEqual(test.registrations[0]['name'], 'Sub')
        self.assertEqual(test.registrations[0]['ob'], lifting3.Sub)

        self.assertEqual(test.registrations[1]['attr'], 'classname')
        self.assertEqual(test.registrations[1]['name'], 'Sub')
        self.assertEqual(test.registrations[1]['ob'], lifting3.Sub)

        self.assertEqual(test.registrations[2]['attr'], 'hiss')
        self.assertEqual(test.registrations[2]['name'], 'Sub')
        self.assertEqual(test.registrations[2]['ob'], lifting3.Sub)

        self.assertEqual(test.registrations[3]['attr'], 'jump')
        self.assertEqual(test.registrations[3]['name'], 'Sub')
        self.assertEqual(test.registrations[3]['ob'], lifting3.Sub)

        self.assertEqual(test.registrations[4]['attr'], 'ram')
        self.assertEqual(test.registrations[4]['name'], 'Sub')
        self.assertEqual(test.registrations[4]['ob'], lifting3.Sub)

        self.assertEqual(test.registrations[5]['attr'], 'smack')
        self.assertEqual(test.registrations[5]['name'], 'Sub')
        self.assertEqual(test.registrations[5]['ob'], lifting3.Sub)

        self.assertEqual(test.registrations[6]['attr'], 'hiss')
        self.assertEqual(test.registrations[6]['name'], 'Super2')
        self.assertEqual(test.registrations[6]['ob'], lifting3.Super2)

        self.assertEqual(test.registrations[7]['attr'], 'jump')
        self.assertEqual(test.registrations[7]['name'], 'Super2')
        self.assertEqual(test.registrations[7]['ob'], lifting3.Super2)

    def test_lifting4(self):
        from venusian.tests.fixtures import lifting4
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(lifting4)
        test.registrations.sort(
            key=lambda x: (x['name'], x['attr'], x['ob'].__module__)
            )
        self.assertEqual(len(test.registrations), 2)

        self.assertEqual(test.registrations[0]['attr'], 'hiss')
        self.assertEqual(test.registrations[0]['name'], 'Sub')
        self.assertEqual(test.registrations[0]['ob'], lifting4.Sub)

        self.assertEqual(test.registrations[1]['attr'], 'smack')
        self.assertEqual(test.registrations[1]['name'], 'Sub')
        self.assertEqual(test.registrations[1]['ob'], lifting4.Sub)

    def test_lifting5(self):
        from venusian.tests.fixtures import lifting5
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(lifting5)
        test.registrations.sort(
            key=lambda x: (x['name'], x['attr'], x['ob'].__module__)
            )
        self.assertEqual(len(test.registrations), 15)

        self.assertEqual(test.registrations[0]['attr'], 'boo')
        self.assertEqual(test.registrations[0]['name'], 'Sub')
        self.assertEqual(test.registrations[0]['ob'], lifting5.Sub)

        self.assertEqual(test.registrations[1]['attr'], 'classname')
        self.assertEqual(test.registrations[1]['name'], 'Sub')
        self.assertEqual(test.registrations[1]['ob'], lifting5.Sub)

        self.assertEqual(test.registrations[2]['attr'], 'hiss')
        self.assertEqual(test.registrations[2]['name'], 'Sub')
        self.assertEqual(test.registrations[2]['ob'], lifting5.Sub)

        self.assertEqual(test.registrations[3]['attr'], 'jump')
        self.assertEqual(test.registrations[3]['name'], 'Sub')
        self.assertEqual(test.registrations[3]['ob'], lifting5.Sub)

        self.assertEqual(test.registrations[4]['attr'], 'ram')
        self.assertEqual(test.registrations[4]['name'], 'Sub')
        self.assertEqual(test.registrations[4]['ob'], lifting5.Sub)

        self.assertEqual(test.registrations[5]['attr'], 'smack')
        self.assertEqual(test.registrations[5]['name'], 'Sub')
        self.assertEqual(test.registrations[5]['ob'], lifting5.Sub)

        self.assertEqual(test.registrations[6]['attr'], 'boo')
        self.assertEqual(test.registrations[6]['name'], 'Super1')
        self.assertEqual(test.registrations[6]['ob'], lifting5.Super1)

        self.assertEqual(test.registrations[7]['attr'], 'classname')
        self.assertEqual(test.registrations[7]['name'], 'Super1')
        self.assertEqual(test.registrations[7]['ob'], lifting5.Super1)

        self.assertEqual(test.registrations[8]['attr'], 'jump')
        self.assertEqual(test.registrations[8]['name'], 'Super1')
        self.assertEqual(test.registrations[8]['ob'], lifting5.Super1)
        
        self.assertEqual(test.registrations[9]['attr'], 'ram')
        self.assertEqual(test.registrations[9]['name'], 'Super1')
        self.assertEqual(test.registrations[9]['ob'], lifting5.Super1)

        self.assertEqual(test.registrations[10]['attr'], 'boo')
        self.assertEqual(test.registrations[10]['name'], 'Super2')
        self.assertEqual(test.registrations[10]['ob'], lifting5.Super2)

        self.assertEqual(test.registrations[11]['attr'], 'classname')
        self.assertEqual(test.registrations[11]['name'], 'Super2')
        self.assertEqual(test.registrations[11]['ob'], lifting5.Super2)

        self.assertEqual(test.registrations[12]['attr'], 'hiss')
        self.assertEqual(test.registrations[12]['name'], 'Super2')
        self.assertEqual(test.registrations[12]['ob'], lifting5.Super2)

        self.assertEqual(test.registrations[13]['attr'], 'jump')
        self.assertEqual(test.registrations[13]['name'], 'Super2')
        self.assertEqual(test.registrations[13]['ob'], lifting5.Super2)

        self.assertEqual(test.registrations[14]['attr'], 'ram')
        self.assertEqual(test.registrations[14]['name'], 'Super2')
        self.assertEqual(test.registrations[14]['ob'], lifting5.Super2)

    def test_subclassing(self):
        from venusian.tests.fixtures import subclassing
        test = Test()
        scanner = self._makeOne(test=test)
        scanner.scan(subclassing)
        test.registrations.sort(
            key=lambda x: (x['name'], x['attr'], x['ob'].__module__)
            )
        self.assertEqual(len(test.registrations), 2)
        
        self.assertEqual(test.registrations[0]['attr'], 'boo')
        self.assertEqual(test.registrations[0]['name'], 'Super')
        self.assertEqual(test.registrations[0]['ob'], subclassing.Super)

        self.assertEqual(test.registrations[1]['attr'], 'classname')
        self.assertEqual(test.registrations[1]['name'], 'Super')
        self.assertEqual(test.registrations[1]['ob'], subclassing.Super)
        
class Test_lift(unittest.TestCase):
    def _makeOne(self, categories=None):
        from venusian import lift
        return lift(categories)

    def test_not_class(self):
        inst = self._makeOne()
        self.assertRaises(RuntimeError, inst, None)

class Test_onlyliftedfrom(unittest.TestCase):
    def _makeOne(self):
        from venusian import onlyliftedfrom
        return onlyliftedfrom()

    def test_not_class(self):
        inst = self._makeOne()
        self.assertRaises(RuntimeError, inst, None)
        
def md(name): # pragma: no cover
    if name in sys.modules:
        del sys.modules[name]
    
