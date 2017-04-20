import unittest
from pyramid import testing

class NewRequestEventTests(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.events import NewRequest
        return NewRequest

    def _makeOne(self, request):
        return self._getTargetClass()(request)

    def test_class_conforms_to_INewRequest(self):
        from pyramid.interfaces import INewRequest
        from zope.interface.verify import verifyClass
        klass = self._getTargetClass()
        verifyClass(INewRequest, klass)

    def test_instance_conforms_to_INewRequest(self):
        from pyramid.interfaces import INewRequest
        from zope.interface.verify import verifyObject
        request = DummyRequest()
        inst = self._makeOne(request)
        verifyObject(INewRequest, inst)

    def test_ctor(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        self.assertEqual(inst.request, request)

class NewResponseEventTests(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.events import NewResponse
        return NewResponse

    def _makeOne(self, request, response):
        return self._getTargetClass()(request, response)

    def test_class_conforms_to_INewResponse(self):
        from pyramid.interfaces import INewResponse
        from zope.interface.verify import verifyClass
        klass = self._getTargetClass()
        verifyClass(INewResponse, klass)

    def test_instance_conforms_to_INewResponse(self):
        from pyramid.interfaces import INewResponse
        from zope.interface.verify import verifyObject
        request = DummyRequest()
        response = DummyResponse()
        inst = self._makeOne(request, response)
        verifyObject(INewResponse, inst)

    def test_ctor(self):
        request = DummyRequest()
        response = DummyResponse()
        inst = self._makeOne(request, response)
        self.assertEqual(inst.request, request)
        self.assertEqual(inst.response, response)

class ApplicationCreatedEventTests(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.events import ApplicationCreated
        return ApplicationCreated

    def _makeOne(self, context=object()):
        return self._getTargetClass()(context)

    def test_class_conforms_to_IApplicationCreated(self):
        from pyramid.interfaces import IApplicationCreated
        from zope.interface.verify import verifyClass
        verifyClass(IApplicationCreated, self._getTargetClass())

    def test_object_conforms_to_IApplicationCreated(self):
        from pyramid.interfaces import IApplicationCreated
        from zope.interface.verify import verifyObject
        verifyObject(IApplicationCreated, self._makeOne())

class WSGIApplicationCreatedEventTests(ApplicationCreatedEventTests):
    def _getTargetClass(self):
        from pyramid.events import WSGIApplicationCreatedEvent
        return WSGIApplicationCreatedEvent

    def test_class_conforms_to_IWSGIApplicationCreatedEvent(self):
        from pyramid.interfaces import IWSGIApplicationCreatedEvent
        from zope.interface.verify import verifyClass
        verifyClass(IWSGIApplicationCreatedEvent, self._getTargetClass())

    def test_object_conforms_to_IWSGIApplicationCreatedEvent(self):
        from pyramid.interfaces import IWSGIApplicationCreatedEvent
        from zope.interface.verify import verifyObject
        verifyObject(IWSGIApplicationCreatedEvent, self._makeOne())

class ContextFoundEventTests(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.events import ContextFound
        return ContextFound

    def _makeOne(self, request=None):
        if request is None:
            request = DummyRequest()
        return self._getTargetClass()(request)

    def test_class_conforms_to_IContextFound(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IContextFound
        verifyClass(IContextFound, self._getTargetClass())

    def test_instance_conforms_to_IContextFound(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IContextFound
        verifyObject(IContextFound, self._makeOne())

class AfterTraversalEventTests(ContextFoundEventTests):
    def _getTargetClass(self):
        from pyramid.events import AfterTraversal
        return AfterTraversal

    def test_class_conforms_to_IAfterTraversal(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IAfterTraversal
        verifyClass(IAfterTraversal, self._getTargetClass())

    def test_instance_conforms_to_IAfterTraversal(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IAfterTraversal
        verifyObject(IAfterTraversal, self._makeOne())

class BeforeTraversalEventTests(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.events import BeforeTraversal
        return BeforeTraversal

    def _makeOne(self, request=None):
        if request is None:
            request = DummyRequest()
        return self._getTargetClass()(request)

    def test_class_conforms_to_IBeforeTraversal(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IBeforeTraversal
        verifyClass(IBeforeTraversal, self._getTargetClass())

    def test_instance_conforms_to_IBeforeTraversal(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IBeforeTraversal
        verifyObject(IBeforeTraversal, self._makeOne())


class TestSubscriber(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _makeOne(self, *ifaces, **predicates):
        from pyramid.events import subscriber
        return subscriber(*ifaces, **predicates)

    def test_register_single(self):
        from zope.interface import Interface
        class IFoo(Interface): pass
        class IBar(Interface): pass
        dec = self._makeOne(IFoo)
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.subscribed, [(foo, IFoo)])

    def test_register_multi(self):
        from zope.interface import Interface
        class IFoo(Interface): pass
        class IBar(Interface): pass
        dec = self._makeOne(IFoo, IBar)
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.subscribed, [(foo, IFoo), (foo, IBar)])

    def test_register_none_means_all(self):
        from zope.interface import Interface
        dec = self._makeOne()
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.subscribed, [(foo, Interface)])

    def test_register_objectevent(self):
        from zope.interface import Interface
        class IFoo(Interface): pass
        class IBar(Interface): pass
        dec = self._makeOne([IFoo, IBar])
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.subscribed, [(foo, [IFoo, IBar])])

    def test___call__(self):
        dec = self._makeOne()
        dummy_venusian = DummyVenusian()
        dec.venusian = dummy_venusian
        def foo(): pass
        dec(foo)
        self.assertEqual(dummy_venusian.attached,
                         [(foo, dec.register, 'pyramid')])

    def test_regsister_with_predicates(self):
        from zope.interface import Interface
        dec = self._makeOne(a=1)
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.subscribed, [(foo, Interface, {'a':1})])

class TestBeforeRender(unittest.TestCase):
    def _makeOne(self, system, val=None):
        from pyramid.events import BeforeRender
        return BeforeRender(system, val)

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IBeforeRender
        event = self._makeOne({})
        verifyObject(IBeforeRender, event)

    def test_setitem_success(self):
        event = self._makeOne({})
        event['a'] = 1
        self.assertEqual(event, {'a':1})

    def test_setdefault_fail(self):
        event = self._makeOne({})
        result = event.setdefault('a', 1)
        self.assertEqual(result, 1)
        self.assertEqual(event, {'a':1})

    def test_setdefault_success(self):
        event = self._makeOne({})
        event['a'] = 1
        result = event.setdefault('a', 2)
        self.assertEqual(result, 1)
        self.assertEqual(event, {'a':1})

    def test_update_success(self):
        event = self._makeOne({'a':1})
        event.update({'b':2})
        self.assertEqual(event, {'a':1, 'b':2})

    def test__contains__True(self):
        system = {'a':1}
        event = self._makeOne(system)
        self.assertTrue('a' in event)

    def test__contains__False(self):
        system = {}
        event = self._makeOne(system)
        self.assertFalse('a' in event)

    def test__getitem__success(self):
        system = {'a':1}
        event = self._makeOne(system)
        self.assertEqual(event['a'], 1)

    def test__getitem__fail(self):
        system = {}
        event = self._makeOne(system)
        self.assertRaises(KeyError, event.__getitem__, 'a')

    def test_get_success(self):
        system = {'a':1}
        event = self._makeOne(system)
        self.assertEqual(event.get('a'), 1)

    def test_get_fail(self):
        system = {}
        event = self._makeOne(system)
        self.assertEqual(event.get('a'), None)

    def test_rendering_val(self):
        system = {}
        val = {}
        event = self._makeOne(system, val)
        self.assertTrue(event.rendering_val is val)

class DummyConfigurator(object):
    def __init__(self):
        self.subscribed = []

    def add_subscriber(self, wrapped, ifaces, **predicates):
        if not predicates:
            self.subscribed.append((wrapped, ifaces))
        else:
            self.subscribed.append((wrapped, ifaces, predicates))

class DummyRegistry(object):
    pass

class DummyVenusian(object):
    def __init__(self):
        self.attached = []

    def attach(self, wrapped, fn, category=None):
        self.attached.append((wrapped, fn, category))

class Dummy:
    pass

class DummyRequest:
    pass

class DummyResponse:
    pass

