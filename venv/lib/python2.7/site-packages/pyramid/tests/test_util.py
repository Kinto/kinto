import unittest
from pyramid.compat import PY3

class Test_InstancePropertyMixin(unittest.TestCase):
    def _makeOne(self):
        cls = self._getTargetClass()
        class Foo(cls):
            pass
        return Foo()

    def _getTargetClass(self):
        from pyramid.util import InstancePropertyMixin
        return InstancePropertyMixin

    def test_callable(self):
        def worker(obj):
            return obj.bar
        foo = self._makeOne()
        foo.set_property(worker)
        foo.bar = 1
        self.assertEqual(1, foo.worker)
        foo.bar = 2
        self.assertEqual(2, foo.worker)

    def test_callable_with_name(self):
        def worker(obj):
            return obj.bar
        foo = self._makeOne()
        foo.set_property(worker, name='x')
        foo.bar = 1
        self.assertEqual(1, foo.x)
        foo.bar = 2
        self.assertEqual(2, foo.x)

    def test_callable_with_reify(self):
        def worker(obj):
            return obj.bar
        foo = self._makeOne()
        foo.set_property(worker, reify=True)
        foo.bar = 1
        self.assertEqual(1, foo.worker)
        foo.bar = 2
        self.assertEqual(1, foo.worker)

    def test_callable_with_name_reify(self):
        def worker(obj):
            return obj.bar
        foo = self._makeOne()
        foo.set_property(worker, name='x')
        foo.set_property(worker, name='y', reify=True)
        foo.bar = 1
        self.assertEqual(1, foo.y)
        self.assertEqual(1, foo.x)
        foo.bar = 2
        self.assertEqual(2, foo.x)
        self.assertEqual(1, foo.y)

    def test_property_without_name(self):
        def worker(obj): pass
        foo = self._makeOne()
        self.assertRaises(ValueError, foo.set_property, property(worker))

    def test_property_with_name(self):
        def worker(obj):
            return obj.bar
        foo = self._makeOne()
        foo.set_property(property(worker), name='x')
        foo.bar = 1
        self.assertEqual(1, foo.x)
        foo.bar = 2
        self.assertEqual(2, foo.x)

    def test_property_with_reify(self):
        def worker(obj): pass
        foo = self._makeOne()
        self.assertRaises(ValueError, foo.set_property,
                          property(worker), name='x', reify=True)

    def test_override_property(self):
        def worker(obj): pass
        foo = self._makeOne()
        foo.set_property(worker, name='x')
        def doit():
            foo.x = 1
        self.assertRaises(AttributeError, doit)

    def test_override_reify(self):
        def worker(obj): pass
        foo = self._makeOne()
        foo.set_property(worker, name='x', reify=True)
        foo.x = 1
        self.assertEqual(1, foo.x)
        foo.x = 2
        self.assertEqual(2, foo.x)

    def test_reset_property(self):
        foo = self._makeOne()
        foo.set_property(lambda _: 1, name='x')
        self.assertEqual(1, foo.x)
        foo.set_property(lambda _: 2, name='x')
        self.assertEqual(2, foo.x)

    def test_reset_reify(self):
        """ This is questionable behavior, but may as well get notified
        if it changes."""
        foo = self._makeOne()
        foo.set_property(lambda _: 1, name='x', reify=True)
        self.assertEqual(1, foo.x)
        foo.set_property(lambda _: 2, name='x', reify=True)
        self.assertEqual(1, foo.x)

    def test__make_property(self):
        from pyramid.decorator import reify
        cls = self._getTargetClass()
        name, fn = cls._make_property(lambda x: 1, name='x', reify=True)
        self.assertEqual(name, 'x')
        self.assertTrue(isinstance(fn, reify))

    def test__set_properties_with_iterable(self):
        foo = self._makeOne()
        x = foo._make_property(lambda _: 1, name='x', reify=True)
        y = foo._make_property(lambda _: 2, name='y')
        foo._set_properties([x, y])
        self.assertEqual(1, foo.x)
        self.assertEqual(2, foo.y)

    def test__set_properties_with_dict(self):
        foo = self._makeOne()
        x_name, x_fn = foo._make_property(lambda _: 1, name='x', reify=True)
        y_name, y_fn = foo._make_property(lambda _: 2, name='y')
        foo._set_properties({x_name: x_fn, y_name: y_fn})
        self.assertEqual(1, foo.x)
        self.assertEqual(2, foo.y)

    def test__set_extensions(self):
        inst = self._makeOne()
        def foo(self, result):
            return result
        n, bar = inst._make_property(lambda _: 'bar', name='bar')
        class Extensions(object):
            def __init__(self):
                self.methods = {'foo':foo}
                self.descriptors = {'bar':bar}
        extensions = Extensions()
        inst._set_extensions(extensions)
        self.assertEqual(inst.bar, 'bar')
        self.assertEqual(inst.foo('abc'), 'abc')

class Test_WeakOrderedSet(unittest.TestCase):
    def _makeOne(self):
        from pyramid.config import WeakOrderedSet
        return WeakOrderedSet()

    def test_ctor(self):
        wos = self._makeOne()
        self.assertEqual(len(wos), 0)
        self.assertEqual(wos.last, None)

    def test_add_item(self):
        wos = self._makeOne()
        reg = Dummy()
        wos.add(reg)
        self.assertEqual(list(wos), [reg])
        self.assertTrue(reg in wos)
        self.assertEqual(wos.last, reg)

    def test_add_multiple_items(self):
        wos = self._makeOne()
        reg1 = Dummy()
        reg2 = Dummy()
        wos.add(reg1)
        wos.add(reg2)
        self.assertEqual(len(wos), 2)
        self.assertEqual(list(wos), [reg1, reg2])
        self.assertTrue(reg1 in wos)
        self.assertTrue(reg2 in wos)
        self.assertEqual(wos.last, reg2)

    def test_add_duplicate_items(self):
        wos = self._makeOne()
        reg = Dummy()
        wos.add(reg)
        wos.add(reg)
        self.assertEqual(len(wos), 1)
        self.assertEqual(list(wos), [reg])
        self.assertTrue(reg in wos)
        self.assertEqual(wos.last, reg)

    def test_weakref_removal(self):
        wos = self._makeOne()
        reg = Dummy()
        wos.add(reg)
        wos.remove(reg)
        self.assertEqual(len(wos), 0)
        self.assertEqual(list(wos), [])
        self.assertEqual(wos.last, None)

    def test_last_updated(self):
        wos = self._makeOne()
        reg = Dummy()
        reg2 = Dummy()
        wos.add(reg)
        wos.add(reg2)
        wos.remove(reg2)
        self.assertEqual(len(wos), 1)
        self.assertEqual(list(wos), [reg])
        self.assertEqual(wos.last, reg)

    def test_empty(self):
        wos = self._makeOne()
        reg = Dummy()
        reg2 = Dummy()
        wos.add(reg)
        wos.add(reg2)
        wos.empty()
        self.assertEqual(len(wos), 0)
        self.assertEqual(list(wos), [])
        self.assertEqual(wos.last, None)

class Test_object_description(unittest.TestCase):
    def _callFUT(self, object):
        from pyramid.util import object_description
        return object_description(object)

    def test_string(self):
        self.assertEqual(self._callFUT('abc'), 'abc')

    def test_int(self):
        self.assertEqual(self._callFUT(1), '1')

    def test_bool(self):
        self.assertEqual(self._callFUT(True), 'True')

    def test_None(self):
        self.assertEqual(self._callFUT(None), 'None')

    def test_float(self):
        self.assertEqual(self._callFUT(1.2), '1.2')

    def test_tuple(self):
        self.assertEqual(self._callFUT(('a', 'b')), "('a', 'b')")

    def test_set(self):
        if PY3: # pragma: no cover
            self.assertEqual(self._callFUT(set(['a'])), "{'a'}")
        else: # pragma: no cover
            self.assertEqual(self._callFUT(set(['a'])), "set(['a'])")

    def test_list(self):
        self.assertEqual(self._callFUT(['a']), "['a']")

    def test_dict(self):
        self.assertEqual(self._callFUT({'a':1}), "{'a': 1}")

    def test_nomodule(self):
        o = object()
        self.assertEqual(self._callFUT(o), 'object %s' % str(o))

    def test_module(self):
        import pyramid
        self.assertEqual(self._callFUT(pyramid), 'module pyramid')

    def test_method(self):
        self.assertEqual(
            self._callFUT(self.test_method),
            'method test_method of class pyramid.tests.test_util.'
            'Test_object_description')

    def test_class(self):
        self.assertEqual(
            self._callFUT(self.__class__),
            'class pyramid.tests.test_util.Test_object_description')

    def test_function(self):
        self.assertEqual(
            self._callFUT(dummyfunc),
            'function pyramid.tests.test_util.dummyfunc')

    def test_instance(self):
        inst = Dummy()
        self.assertEqual(
            self._callFUT(inst),
            "object %s" % str(inst))
        
    def test_shortened_repr(self):
        inst = ['1'] * 1000
        self.assertEqual(
            self._callFUT(inst),
            str(inst)[:100] + ' ... ]')

class TestTopologicalSorter(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.util import TopologicalSorter
        return TopologicalSorter(*arg, **kw)

    def test_remove(self):
        inst = self._makeOne()
        inst.names.append('name')
        inst.name2val['name'] = 1
        inst.req_after.add('name')
        inst.req_before.add('name')
        inst.name2after['name'] = ('bob',)
        inst.name2before['name'] = ('fred',)
        inst.order.append(('bob', 'name'))
        inst.order.append(('name', 'fred'))
        inst.remove('name')
        self.assertFalse(inst.names)
        self.assertFalse(inst.req_before)
        self.assertFalse(inst.req_after)
        self.assertFalse(inst.name2before)
        self.assertFalse(inst.name2after)
        self.assertFalse(inst.name2val)
        self.assertFalse(inst.order)

    def test_add(self):
        from pyramid.util import LAST
        sorter = self._makeOne()
        sorter.add('name', 'factory')
        self.assertEqual(sorter.names, ['name'])
        self.assertEqual(sorter.name2val,
                         {'name':'factory'})
        self.assertEqual(sorter.order, [('name', LAST)])
        sorter.add('name2', 'factory2')
        self.assertEqual(sorter.names, ['name',  'name2'])
        self.assertEqual(sorter.name2val,
                         {'name':'factory', 'name2':'factory2'})
        self.assertEqual(sorter.order,
                         [('name', LAST), ('name2', LAST)])
        sorter.add('name3', 'factory3', before='name2')
        self.assertEqual(sorter.names,
                         ['name',  'name2', 'name3'])
        self.assertEqual(sorter.name2val,
                         {'name':'factory', 'name2':'factory2',
                          'name3':'factory3'})
        self.assertEqual(sorter.order,
                         [('name', LAST), ('name2', LAST),
                          ('name3', 'name2')])

    def test_sorted_ordering_1(self):
        sorter = self._makeOne()
        sorter.add('name1', 'factory1')
        sorter.add('name2', 'factory2')
        self.assertEqual(sorter.sorted(),
                         [
                             ('name1', 'factory1'),
                             ('name2', 'factory2'),
                             ])

    def test_sorted_ordering_2(self):
        from pyramid.util import FIRST
        sorter = self._makeOne()
        sorter.add('name1', 'factory1')
        sorter.add('name2', 'factory2', after=FIRST)
        self.assertEqual(sorter.sorted(),
                         [
                             ('name2', 'factory2'),
                             ('name1', 'factory1'),
                             ])

    def test_sorted_ordering_3(self):
        from pyramid.util import FIRST
        sorter = self._makeOne()
        add = sorter.add
        add('auth', 'auth_factory', after='browserid')
        add('dbt', 'dbt_factory') 
        add('retry', 'retry_factory', before='txnmgr', after='exceptionview')
        add('browserid', 'browserid_factory')
        add('txnmgr', 'txnmgr_factory', after='exceptionview')
        add('exceptionview', 'excview_factory', after=FIRST)
        self.assertEqual(sorter.sorted(),
                         [
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('txnmgr', 'txnmgr_factory'),
                             ('dbt', 'dbt_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ])

    def test_sorted_ordering_4(self):
        from pyramid.util import FIRST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory', after=FIRST)
        add('auth', 'auth_factory', after='browserid')
        add('retry', 'retry_factory', before='txnmgr', after='exceptionview')
        add('browserid', 'browserid_factory')
        add('txnmgr', 'txnmgr_factory', after='exceptionview')
        add('dbt', 'dbt_factory') 
        self.assertEqual(sorter.sorted(),
                         [
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('txnmgr', 'txnmgr_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('dbt', 'dbt_factory'),
                             ])

    def test_sorted_ordering_5(self):
        from pyramid.util import LAST, FIRST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory')
        add('auth', 'auth_factory', after=FIRST)
        add('retry', 'retry_factory', before='txnmgr', after='exceptionview')
        add('browserid', 'browserid_factory', after=FIRST)
        add('txnmgr', 'txnmgr_factory', after='exceptionview', before=LAST)
        add('dbt', 'dbt_factory') 
        self.assertEqual(sorter.sorted(),
                         [
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('txnmgr', 'txnmgr_factory'), 
                             ('dbt', 'dbt_factory'),
                             ])

    def test_sorted_ordering_missing_before_partial(self):
        from pyramid.exceptions import ConfigurationError
        sorter = self._makeOne()
        add = sorter.add
        add('dbt', 'dbt_factory')
        add('auth', 'auth_factory', after='browserid')
        add('retry', 'retry_factory', before='txnmgr', after='exceptionview')
        add('browserid', 'browserid_factory')
        self.assertRaises(ConfigurationError, sorter.sorted)

    def test_sorted_ordering_missing_after_partial(self):
        from pyramid.exceptions import ConfigurationError
        sorter = self._makeOne()
        add = sorter.add
        add('dbt', 'dbt_factory')
        add('auth', 'auth_factory', after='txnmgr')
        add('retry', 'retry_factory', before='dbt', after='exceptionview')
        add('browserid', 'browserid_factory')
        self.assertRaises(ConfigurationError, sorter.sorted)

    def test_sorted_ordering_missing_before_and_after_partials(self):
        from pyramid.exceptions import ConfigurationError
        sorter = self._makeOne()
        add = sorter.add
        add('dbt', 'dbt_factory')
        add('auth', 'auth_factory', after='browserid')
        add('retry', 'retry_factory', before='foo', after='txnmgr')
        add('browserid', 'browserid_factory')
        self.assertRaises(ConfigurationError, sorter.sorted)

    def test_sorted_ordering_missing_before_partial_with_fallback(self):
        from pyramid.util import LAST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory', before=LAST)
        add('auth', 'auth_factory', after='browserid')
        add('retry', 'retry_factory', before=('txnmgr', LAST),
                                      after='exceptionview')
        add('browserid', 'browserid_factory')
        add('dbt', 'dbt_factory') 
        self.assertEqual(sorter.sorted(),
                         [
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('dbt', 'dbt_factory'),
                             ])

    def test_sorted_ordering_missing_after_partial_with_fallback(self):
        from pyramid.util import FIRST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory', after=FIRST)
        add('auth', 'auth_factory', after=('txnmgr','browserid'))
        add('retry', 'retry_factory', after='exceptionview')
        add('browserid', 'browserid_factory')
        add('dbt', 'dbt_factory')
        self.assertEqual(sorter.sorted(),
                         [
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ('browserid', 'browserid_factory'),
                             ('auth', 'auth_factory'),
                             ('dbt', 'dbt_factory'),
                             ])

    def test_sorted_ordering_with_partial_fallbacks(self):
        from pyramid.util import LAST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory', before=('wontbethere', LAST))
        add('retry', 'retry_factory', after='exceptionview')
        add('browserid', 'browserid_factory', before=('wont2', 'exceptionview'))
        self.assertEqual(sorter.sorted(),
                         [
                             ('browserid', 'browserid_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ])

    def test_sorted_ordering_with_multiple_matching_fallbacks(self):
        from pyramid.util import LAST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory', before=LAST)
        add('retry', 'retry_factory', after='exceptionview')
        add('browserid', 'browserid_factory', before=('retry', 'exceptionview'))
        self.assertEqual(sorter.sorted(),
                         [
                             ('browserid', 'browserid_factory'),
                             ('exceptionview', 'excview_factory'),
                             ('retry', 'retry_factory'),
                             ])

    def test_sorted_ordering_with_missing_fallbacks(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.util import LAST
        sorter = self._makeOne()
        add = sorter.add
        add('exceptionview', 'excview_factory', before=LAST)
        add('retry', 'retry_factory', after='exceptionview')
        add('browserid', 'browserid_factory', before=('txnmgr', 'auth'))
        self.assertRaises(ConfigurationError, sorter.sorted)

    def test_sorted_ordering_conflict_direct(self):
        from pyramid.exceptions import CyclicDependencyError
        sorter = self._makeOne()
        add = sorter.add
        add('browserid', 'browserid_factory')
        add('auth', 'auth_factory', before='browserid', after='browserid')
        self.assertRaises(CyclicDependencyError, sorter.sorted)

    def test_sorted_ordering_conflict_indirect(self):
        from pyramid.exceptions import CyclicDependencyError
        sorter = self._makeOne()
        add = sorter.add
        add('browserid', 'browserid_factory')
        add('auth', 'auth_factory', before='browserid')
        add('dbt', 'dbt_factory', after='browserid', before='auth')
        self.assertRaises(CyclicDependencyError, sorter.sorted)

class TestSentinel(unittest.TestCase):
    def test_repr(self):
        from pyramid.util import Sentinel
        r = repr(Sentinel('ABC'))
        self.assertEqual(r, 'ABC')

class TestActionInfo(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.util import ActionInfo
        return ActionInfo
        
    def _makeOne(self, filename, lineno, function, linerepr):
        return self._getTargetClass()(filename, lineno, function, linerepr)

    def test_class_conforms(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IActionInfo
        verifyClass(IActionInfo, self._getTargetClass())

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IActionInfo
        verifyObject(IActionInfo, self._makeOne('f', 0, 'f', 'f'))

    def test_ctor(self):
        inst = self._makeOne('filename', 10, 'function', 'src')
        self.assertEqual(inst.file, 'filename')
        self.assertEqual(inst.line, 10)
        self.assertEqual(inst.function, 'function')
        self.assertEqual(inst.src, 'src')

    def test___str__(self):
        inst = self._makeOne('filename', 0, 'function', '   linerepr  ')
        self.assertEqual(str(inst),
                         "Line 0 of file filename:\n       linerepr  ")


def dummyfunc(): pass

class Dummy(object):
    pass
