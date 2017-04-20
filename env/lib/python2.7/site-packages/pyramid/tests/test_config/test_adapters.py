import unittest

from pyramid.compat import PY2
from pyramid.tests.test_config import IDummy

class AdaptersConfiguratorMixinTests(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_add_subscriber_defaults(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            pass
        L = []
        def subscriber(event):
            L.append(event)
        config = self._makeOne(autocommit=True)
        config.add_subscriber(subscriber)
        event = Event()
        config.registry.notify(event)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.notify(object())
        self.assertEqual(len(L), 2)

    def test_add_subscriber_iface_specified(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            pass
        L = []
        def subscriber(event):
            L.append(event)
        config = self._makeOne(autocommit=True)
        config.add_subscriber(subscriber, IEvent)
        event = Event()
        config.registry.notify(event)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.notify(object())
        self.assertEqual(len(L), 1)

    def test_add_subscriber_dottednames(self):
        import pyramid.tests.test_config
        from pyramid.interfaces import INewRequest
        config = self._makeOne(autocommit=True)
        config.add_subscriber('pyramid.tests.test_config',
                              'pyramid.interfaces.INewRequest')
        handlers = list(config.registry.registeredHandlers())
        self.assertEqual(len(handlers), 1)
        handler = handlers[0]
        self.assertEqual(handler.handler, pyramid.tests.test_config)
        self.assertEqual(handler.required, (INewRequest,))

    def test_add_object_event_subscriber(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            object = 'foo'
        event = Event()
        L = []
        def subscriber(object, event):
            L.append(event)
        config = self._makeOne(autocommit=True)
        config.add_subscriber(subscriber, (Interface, IEvent))
        config.registry.subscribers((event.object, event), None)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.subscribers((event.object, IDummy), None)
        self.assertEqual(len(L), 1)

    def test_add_subscriber_with_specific_type_and_predicates_True(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            pass
        L = []
        def subscriber(event):
            L.append(event)
        config = self._makeOne(autocommit=True)
        predlist = config.get_predlist('subscriber')
        jam_predicate = predicate_maker('jam')
        jim_predicate = predicate_maker('jim')
        predlist.add('jam', jam_predicate)
        predlist.add('jim', jim_predicate)
        config.add_subscriber(subscriber, IEvent, jam=True, jim=True)
        event = Event()
        event.jam = True
        event.jim = True
        config.registry.notify(event)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.notify(object())
        self.assertEqual(len(L), 1)

    def test_add_subscriber_with_default_type_predicates_True(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            pass
        L = []
        def subscriber(event):
            L.append(event)
        config = self._makeOne(autocommit=True)
        predlist = config.get_predlist('subscriber')
        jam_predicate = predicate_maker('jam')
        jim_predicate = predicate_maker('jim')
        predlist.add('jam', jam_predicate)
        predlist.add('jim', jim_predicate)
        config.add_subscriber(subscriber, jam=True, jim=True)
        event = Event()
        event.jam = True
        event.jim = True
        config.registry.notify(event)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.notify(object())
        self.assertEqual(len(L), 1)

    def test_add_subscriber_with_specific_type_and_predicates_False(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            pass
        L = []
        def subscriber(event): L.append(event)
        config = self._makeOne(autocommit=True)
        predlist = config.get_predlist('subscriber')
        jam_predicate = predicate_maker('jam')
        jim_predicate = predicate_maker('jim')
        predlist.add('jam', jam_predicate)
        predlist.add('jim', jim_predicate)
        config.add_subscriber(subscriber, IEvent, jam=True, jim=True)
        event = Event()
        event.jam = True
        event.jim = False
        config.registry.notify(event)
        self.assertEqual(len(L), 0)

    def test_add_subscriber_with_default_type_predicates_False(self):
        from zope.interface import implementer
        from zope.interface import Interface
        class IEvent(Interface):
            pass
        @implementer(IEvent)
        class Event:
            pass
        L = []
        def subscriber(event): L.append(event)
        config = self._makeOne(autocommit=True)
        predlist = config.get_predlist('subscriber')
        jam_predicate = predicate_maker('jam')
        jim_predicate = predicate_maker('jim')
        predlist.add('jam', jam_predicate)
        predlist.add('jim', jim_predicate)
        config.add_subscriber(subscriber, jam=True, jim=True)
        event = Event()
        event.jam = False
        event.jim = True
        config.registry.notify(event)
        self.assertEqual(len(L), 0)

    def test_add_subscriber_predicate(self):
        config = self._makeOne()
        L = []
        def add_predicate(type, name, factory, weighs_less_than=None,
                          weighs_more_than=None):
            self.assertEqual(type, 'subscriber')
            self.assertEqual(name, 'name')
            self.assertEqual(factory, 'factory')
            self.assertEqual(weighs_more_than, 1)
            self.assertEqual(weighs_less_than, 2)
            L.append(1)
        config._add_predicate = add_predicate
        config.add_subscriber_predicate('name', 'factory', 1, 2)
        self.assertTrue(L)
        
    def test_add_response_adapter(self):
        from pyramid.interfaces import IResponse
        config = self._makeOne(autocommit=True)
        class Adapter(object):
            def __init__(self, other):
                self.other = other
        config.add_response_adapter(Adapter, str)
        result = config.registry.queryAdapter('foo', IResponse)
        self.assertTrue(result.other, 'foo')

    def test_add_response_adapter_self(self):
        from pyramid.interfaces import IResponse
        config = self._makeOne(autocommit=True)
        class Adapter(object):
            pass
        config.add_response_adapter(None, Adapter)
        adapter = Adapter()
        result = config.registry.queryAdapter(adapter, IResponse)
        self.assertTrue(result is adapter)

    def test_add_response_adapter_dottednames(self):
        from pyramid.interfaces import IResponse
        config = self._makeOne(autocommit=True)
        if PY2:
            str_name = '__builtin__.str'
        else:
            str_name = 'builtins.str'
        config.add_response_adapter('pyramid.response.Response', str_name)
        result = config.registry.queryAdapter('foo', IResponse)
        self.assertTrue(result.body, b'foo')

    def test_add_traverser_dotted_names(self):
        from pyramid.interfaces import ITraverser
        config = self._makeOne(autocommit=True)
        config.add_traverser(
            'pyramid.tests.test_config.test_adapters.DummyTraverser',
            'pyramid.tests.test_config.test_adapters.DummyIface')
        iface = DummyIface()
        traverser = config.registry.getAdapter(iface, ITraverser)
        self.assertEqual(traverser.__class__, DummyTraverser)
        self.assertEqual(traverser.root, iface)

    def test_add_traverser_default_iface_means_Interface(self):
        from pyramid.interfaces import ITraverser
        config = self._makeOne(autocommit=True)
        config.add_traverser(DummyTraverser)
        traverser = config.registry.getAdapter(None, ITraverser)
        self.assertEqual(traverser.__class__, DummyTraverser)

    def test_add_traverser_nondefault_iface(self):
        from pyramid.interfaces import ITraverser
        config = self._makeOne(autocommit=True)
        config.add_traverser(DummyTraverser, DummyIface)
        iface = DummyIface()
        traverser = config.registry.getAdapter(iface, ITraverser)
        self.assertEqual(traverser.__class__, DummyTraverser)
        self.assertEqual(traverser.root, iface)
        
    def test_add_traverser_introspectables(self):
        config = self._makeOne()
        config.add_traverser(DummyTraverser, DummyIface)
        actions = config.action_state.actions
        self.assertEqual(len(actions), 1)
        intrs  = actions[0]['introspectables']
        self.assertEqual(len(intrs), 1)
        intr = intrs[0]
        self.assertEqual(intr.type_name, 'traverser')
        self.assertEqual(intr.discriminator, ('traverser', DummyIface))
        self.assertEqual(intr.category_name, 'traversers')
        self.assertEqual(intr.title, 'traverser for %r' % DummyIface)
        self.assertEqual(intr['adapter'], DummyTraverser)
        self.assertEqual(intr['iface'], DummyIface)

    def test_add_resource_url_adapter_dotted_names(self):
        from pyramid.interfaces import IResourceURL
        config = self._makeOne(autocommit=True)
        config.add_resource_url_adapter(
            'pyramid.tests.test_config.test_adapters.DummyResourceURL',
            'pyramid.tests.test_config.test_adapters.DummyIface',
            )
        iface = DummyIface()
        adapter = config.registry.getMultiAdapter((iface, iface), 
                                                    IResourceURL)
        self.assertEqual(adapter.__class__, DummyResourceURL)
        self.assertEqual(adapter.resource, iface)
        self.assertEqual(adapter.request, iface)

    def test_add_resource_url_default_resource_iface_means_Interface(self):
        from pyramid.interfaces import IResourceURL
        config = self._makeOne(autocommit=True)
        config.add_resource_url_adapter(DummyResourceURL)
        iface = DummyIface()
        adapter = config.registry.getMultiAdapter((iface, iface), 
                                                    IResourceURL)
        self.assertEqual(adapter.__class__, DummyResourceURL)
        self.assertEqual(adapter.resource, iface)
        self.assertEqual(adapter.request, iface)

    def test_add_resource_url_nodefault_resource_iface(self):
        from zope.interface import Interface
        from pyramid.interfaces import IResourceURL
        config = self._makeOne(autocommit=True)
        config.add_resource_url_adapter(DummyResourceURL, DummyIface)
        iface = DummyIface()
        adapter = config.registry.getMultiAdapter((iface, iface), 
                                                    IResourceURL)
        self.assertEqual(adapter.__class__, DummyResourceURL)
        self.assertEqual(adapter.resource, iface)
        self.assertEqual(adapter.request, iface)
        bad_result = config.registry.queryMultiAdapter(
            (Interface, Interface),
            IResourceURL,
            )
        self.assertEqual(bad_result, None)

    def test_add_resource_url_adapter_introspectables(self):
        config = self._makeOne()
        config.add_resource_url_adapter(DummyResourceURL, DummyIface)
        actions = config.action_state.actions
        self.assertEqual(len(actions), 1)
        intrs  = actions[0]['introspectables']
        self.assertEqual(len(intrs), 1)
        intr = intrs[0]
        self.assertEqual(intr.type_name, 'resource url adapter')
        self.assertEqual(intr.discriminator, 
                         ('resource url adapter', DummyIface))
        self.assertEqual(intr.category_name, 'resource url adapters')
        self.assertEqual(
            intr.title,
            "resource url adapter for resource iface "
            "<class 'pyramid.tests.test_config.test_adapters.DummyIface'>"
            )
        self.assertEqual(intr['adapter'], DummyResourceURL)
        self.assertEqual(intr['resource_iface'], DummyIface)

class Test_eventonly(unittest.TestCase):
    def _callFUT(self, callee):
        from pyramid.config.adapters import eventonly
        return eventonly(callee)

    def test_defaults(self):
        def acallable(event, a=1, b=2): pass
        self.assertTrue(self._callFUT(acallable))

class DummyTraverser(object):
    def __init__(self, root):
        self.root = root

class DummyIface(object):
    pass

class DummyResourceURL(object):
    def __init__(self, resource, request):
        self.resource = resource
        self.request = request
        
def predicate_maker(name):
    class Predicate(object):
        def __init__(self, val, config):
            self.val = val
        def phash(self):
            return 'phash'
        text = phash
        def __call__(self, event):
            return getattr(event, name, None) == self.val
    return Predicate

