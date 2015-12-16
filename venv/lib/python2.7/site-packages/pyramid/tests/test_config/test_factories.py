import unittest

from pyramid.tests.test_config import dummyfactory

class TestFactoriesMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_set_request_factory(self):
        from pyramid.interfaces import IRequestFactory
        config = self._makeOne(autocommit=True)
        factory = object()
        config.set_request_factory(factory)
        self.assertEqual(config.registry.getUtility(IRequestFactory), factory)

    def test_set_request_factory_dottedname(self):
        from pyramid.interfaces import IRequestFactory
        config = self._makeOne(autocommit=True)
        config.set_request_factory(
            'pyramid.tests.test_config.dummyfactory')
        self.assertEqual(config.registry.getUtility(IRequestFactory),
                         dummyfactory)

    def test_set_root_factory(self):
        from pyramid.interfaces import IRootFactory
        config = self._makeOne()
        config.set_root_factory(dummyfactory)
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(IRootFactory), dummyfactory)

    def test_set_root_factory_as_None(self):
        from pyramid.interfaces import IRootFactory
        from pyramid.traversal import DefaultRootFactory
        config = self._makeOne()
        config.set_root_factory(None)
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(IRootFactory),
                         DefaultRootFactory)

    def test_set_root_factory_dottedname(self):
        from pyramid.interfaces import IRootFactory
        config = self._makeOne()
        config.set_root_factory('pyramid.tests.test_config.dummyfactory')
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(IRootFactory), dummyfactory)

    def test_set_session_factory(self):
        from pyramid.interfaces import ISessionFactory
        config = self._makeOne()
        config.set_session_factory(dummyfactory)
        self.assertEqual(config.registry.queryUtility(ISessionFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(ISessionFactory),
                         dummyfactory)

    def test_set_session_factory_dottedname(self):
        from pyramid.interfaces import ISessionFactory
        config = self._makeOne()
        config.set_session_factory('pyramid.tests.test_config.dummyfactory')
        self.assertEqual(config.registry.queryUtility(ISessionFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(ISessionFactory),
                         dummyfactory)

    def test_add_request_method_with_callable(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne(autocommit=True)
        callable = lambda x: None
        config.add_request_method(callable, name='foo')
        exts = config.registry.getUtility(IRequestExtensions)
        self.assertTrue('foo' in exts.methods)

    def test_add_request_method_with_unnamed_callable(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne(autocommit=True)
        def foo(self): pass
        config.add_request_method(foo)
        exts = config.registry.getUtility(IRequestExtensions)
        self.assertTrue('foo' in exts.methods)

    def test_set_multiple_request_methods_conflict(self):
        from pyramid.exceptions import ConfigurationConflictError
        config = self._makeOne()
        def foo(self): pass
        def bar(self): pass
        config.add_request_method(foo, name='bar')
        config.add_request_method(bar, name='bar')
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_add_request_method_with_None_callable(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne(autocommit=True)
        config.add_request_method(name='foo')
        exts = config.registry.queryUtility(IRequestExtensions)
        self.assertTrue(exts is None)

    def test_add_request_method_with_None_callable_conflict(self):
        from pyramid.exceptions import ConfigurationConflictError
        config = self._makeOne()
        def bar(self): pass
        config.add_request_method(name='foo')
        config.add_request_method(bar, name='foo')
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_add_request_method_with_None_callable_and_no_name(self):
        config = self._makeOne(autocommit=True)
        self.assertRaises(AttributeError, config.add_request_method)


class TestDeprecatedFactoriesMixinMethods(unittest.TestCase):
    def setUp(self):
        from zope.deprecation import __show__
        __show__.off()

    def tearDown(self):
        from zope.deprecation import __show__
        __show__.on()
        
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_set_request_property_with_callable(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne(autocommit=True)
        callable = lambda x: None
        config.set_request_property(callable, name='foo')
        exts = config.registry.getUtility(IRequestExtensions)
        self.assertTrue('foo' in exts.descriptors)

    def test_set_request_property_with_unnamed_callable(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne(autocommit=True)
        def foo(self): pass
        config.set_request_property(foo, reify=True)
        exts = config.registry.getUtility(IRequestExtensions)
        self.assertTrue('foo' in exts.descriptors)

    def test_set_request_property_with_property(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne(autocommit=True)
        callable = property(lambda x: None)
        config.set_request_property(callable, name='foo')
        exts = config.registry.getUtility(IRequestExtensions)
        self.assertTrue('foo' in exts.descriptors)

    def test_set_multiple_request_properties(self):
        from pyramid.interfaces import IRequestExtensions
        config = self._makeOne()
        def foo(self): pass
        bar = property(lambda x: None)
        config.set_request_property(foo, reify=True)
        config.set_request_property(bar, name='bar')
        config.commit()
        exts = config.registry.getUtility(IRequestExtensions)
        self.assertTrue('foo' in exts.descriptors)
        self.assertTrue('bar' in exts.descriptors)

    def test_set_multiple_request_properties_conflict(self):
        from pyramid.exceptions import ConfigurationConflictError
        config = self._makeOne()
        def foo(self): pass
        bar = property(lambda x: None)
        config.set_request_property(foo, name='bar', reify=True)
        config.set_request_property(bar, name='bar')
        self.assertRaises(ConfigurationConflictError, config.commit)

    
