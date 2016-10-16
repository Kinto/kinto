import unittest

class Test_get_root(unittest.TestCase):
    def _callFUT(self, app, request=None):
        from pyramid.scripting import get_root
        return get_root(app, request)

    def _makeRegistry(self):
        return DummyRegistry([DummyFactory])

    def test_it_norequest(self):
        registry = self._makeRegistry()
        app = DummyApp(registry=registry)
        root, closer = self._callFUT(app)
        self.assertEqual(len(app.threadlocal_manager.pushed), 1)
        pushed = app.threadlocal_manager.pushed[0]
        self.assertEqual(pushed['registry'], registry)
        self.assertEqual(pushed['request'].registry, app.registry)
        self.assertEqual(len(app.threadlocal_manager.popped), 0)
        closer()
        self.assertEqual(len(app.threadlocal_manager.popped), 1)

    def test_it_withrequest(self):
        registry = self._makeRegistry()
        app = DummyApp(registry=registry)
        request = DummyRequest({})
        root, closer = self._callFUT(app, request)
        self.assertEqual(len(app.threadlocal_manager.pushed), 1)
        pushed = app.threadlocal_manager.pushed[0]
        self.assertEqual(pushed['registry'], registry)
        self.assertEqual(pushed['request'], request)
        self.assertEqual(len(app.threadlocal_manager.popped), 0)
        closer()
        self.assertEqual(len(app.threadlocal_manager.popped), 1)

    def test_it_requestfactory_overridden(self):
        registry = self._makeRegistry()
        app = DummyApp(registry=registry)
        root, closer = self._callFUT(app)
        self.assertEqual(len(app.threadlocal_manager.pushed), 1)
        pushed = app.threadlocal_manager.pushed[0]
        self.assertEqual(pushed['request'].environ['path'], '/')

class Test_prepare(unittest.TestCase):
    def _callFUT(self, request=None, registry=None):
        from pyramid.scripting import prepare
        return prepare(request, registry)

    def _makeRegistry(self, L=None):
        if L is None:
            L = [None, DummyFactory]
        return DummyRegistry(L)

    def setUp(self):
        from pyramid.threadlocal import manager
        self.manager = manager
        self.default = manager.get()

    def test_it_no_valid_apps(self):
        from pyramid.exceptions import ConfigurationError
        self.assertRaises(ConfigurationError, self._callFUT)

    def test_it_norequest(self):
        registry = self._makeRegistry([DummyFactory, None, DummyFactory])
        info = self._callFUT(registry=registry)
        root, closer, request = info['root'], info['closer'], info['request']
        pushed = self.manager.get()
        self.assertEqual(pushed['registry'], registry)
        self.assertEqual(pushed['request'].registry, registry)
        self.assertEqual(root.a, (pushed['request'],))
        closer()
        self.assertEqual(self.default, self.manager.get())
        self.assertEqual(request.context, root)

    def test_it_withrequest_hasregistry(self):
        request = DummyRequest({})
        registry = request.registry = self._makeRegistry()
        info = self._callFUT(request=request)
        root, closer, request = info['root'], info['closer'], info['request']
        pushed = self.manager.get()
        self.assertEqual(pushed['request'], request)
        self.assertEqual(pushed['registry'], registry)
        self.assertEqual(pushed['request'].registry, registry)
        self.assertEqual(root.a, (request,))
        closer()
        self.assertEqual(self.default, self.manager.get())
        self.assertEqual(request.context, root)
        self.assertEqual(request.registry, registry)

    def test_it_withrequest_noregistry(self):
        request = DummyRequest({})
        registry = self._makeRegistry()
        info = self._callFUT(request=request, registry=registry)
        root, closer, request = info['root'], info['closer'], info['request']
        closer()
        self.assertEqual(request.context, root)
        # should be set by prepare
        self.assertEqual(request.registry, registry)

    def test_it_with_request_and_registry(self):
        request = DummyRequest({})
        registry = request.registry = self._makeRegistry()
        info = self._callFUT(request=request, registry=registry)
        root, closer, root = info['root'], info['closer'], info['root']
        pushed = self.manager.get()
        self.assertEqual(pushed['request'], request)
        self.assertEqual(pushed['registry'], registry)
        self.assertEqual(pushed['request'].registry, registry)
        self.assertEqual(root.a, (request,))
        closer()
        self.assertEqual(self.default, self.manager.get())
        self.assertEqual(request.context, root)

    def test_it_with_request_context_already_set(self):
        request = DummyRequest({})
        context = Dummy()
        request.context = context
        registry = request.registry = self._makeRegistry()
        info = self._callFUT(request=request, registry=registry)
        root, closer, root = info['root'], info['closer'], info['root']
        closer()
        self.assertEqual(request.context, context)

    def test_it_with_extensions(self):
        from pyramid.util import InstancePropertyHelper
        exts = DummyExtensions()
        ext_method = lambda r: 'bar'
        name, fn = InstancePropertyHelper.make_property(ext_method, 'foo')
        exts.descriptors[name] = fn
        request = DummyRequest({})
        registry = request.registry = self._makeRegistry([exts, DummyFactory])
        info = self._callFUT(request=request, registry=registry)
        self.assertEqual(request.foo, 'bar')
        root, closer = info['root'], info['closer']
        closer()

class Test__make_request(unittest.TestCase):
    def _callFUT(self, path='/', registry=None):
        from pyramid.scripting import _make_request
        return _make_request(path, registry)

    def _makeRegistry(self):
        return DummyRegistry([DummyFactory])

    def test_it_with_registry(self):
        registry = self._makeRegistry()
        request = self._callFUT('/', registry)
        self.assertEqual(request.environ['path'], '/')
        self.assertEqual(request.registry, registry)

    def test_it_with_no_registry(self):
        from pyramid.config import global_registries
        registry = self._makeRegistry()
        global_registries.add(registry)
        try:
            request = self._callFUT('/hello')
            self.assertEqual(request.environ['path'], '/hello')
            self.assertEqual(request.registry, registry)
        finally:
            global_registries.empty()

class Dummy:
    pass

dummy_root = Dummy()

class DummyFactory(object):
    @classmethod
    def blank(cls, path):
        req = DummyRequest({'path': path})
        return req

    def __init__(self, *a, **kw):
        self.a = a
        self.kw = kw

class DummyRegistry(object):
    def __init__(self, utilities):
        self.utilities = utilities

    def queryUtility(self, iface, default=None): # pragma: no cover
        if self.utilities:
            return self.utilities.pop(0)
        return default

class DummyApp:
    def __init__(self, registry=None):
        self.threadlocal_manager = DummyThreadLocalManager()
        if registry:
            self.registry = registry

    def root_factory(self, environ):
        return dummy_root

class DummyThreadLocalManager:
    def __init__(self):
        self.pushed = []
        self.popped = []
        
    def push(self, item):
        self.pushed.append(item)

    def pop(self):
        self.popped.append(True)
        
class DummyRequest(object):
    matchdict = None
    matched_route = None
    def __init__(self, environ):
        self.environ = environ

class DummyExtensions:
    def __init__(self):
        self.descriptors = {}
        self.methods = {}
