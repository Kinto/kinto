import unittest
import sys

from zope.interface import implementer

from pyramid import testing

class BaseTest(object):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _registerView(self, reg, app, name):
        from pyramid.interfaces import IRequest
        from pyramid.interfaces import IViewClassifier
        for_ = (IViewClassifier, IRequest, IContext)
        from pyramid.interfaces import IView
        reg.registerAdapter(app, for_, IView, name)

    def _makeEnviron(self, **extras):
        environ = {
            'wsgi.url_scheme':'http',
            'wsgi.version':(1,0),
            'SERVER_NAME':'localhost',
            'SERVER_PORT':'8080',
            'REQUEST_METHOD':'GET',
            'PATH_INFO':'/',
            }
        environ.update(extras)
        return environ

    def _makeRequest(self, **environ):
        from pyramid.interfaces import IRequest
        from zope.interface import directlyProvides
        from webob import Request
        from pyramid.registry import Registry
        environ = self._makeEnviron(**environ)
        request = Request(environ)
        request.registry = Registry()
        directlyProvides(request, IRequest)
        return request

    def _makeContext(self):
        from zope.interface import directlyProvides
        context = DummyContext()
        directlyProvides(context, IContext)
        return context

class Test_notfound_view_config(BaseTest, unittest.TestCase):
    def _makeOne(self, **kw):
        from pyramid.view import notfound_view_config
        return notfound_view_config(**kw)

    def test_ctor(self):
        inst = self._makeOne(attr='attr', path_info='path_info', 
                             append_slash=True)
        self.assertEqual(inst.__dict__,
                         {'attr':'attr', 'path_info':'path_info',
                          'append_slash':True})

    def test_it_function(self):
        def view(request): pass
        decorator = self._makeOne(attr='attr', renderer='renderer',
                                  append_slash=True)
        venusian = DummyVenusian()
        decorator.venusian = venusian
        wrapped = decorator(view)
        self.assertTrue(wrapped is view)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(
            settings, 
            [{'attr': 'attr', 'venusian': venusian, 'append_slash': True, 
              'renderer': 'renderer', '_info': 'codeinfo', 'view': None}]
            )

    def test_it_class(self):
        decorator = self._makeOne()
        venusian = DummyVenusian()
        decorator.venusian = venusian
        decorator.venusian.info.scope = 'class'
        class view(object): pass
        wrapped = decorator(view)
        self.assertTrue(wrapped is view)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        self.assertEqual(len(settings[0]), 4)
        self.assertEqual(settings[0]['venusian'], venusian)
        self.assertEqual(settings[0]['view'], None) # comes from call_venusian
        self.assertEqual(settings[0]['attr'], 'view')
        self.assertEqual(settings[0]['_info'], 'codeinfo')

class Test_forbidden_view_config(BaseTest, unittest.TestCase):
    def _makeOne(self, **kw):
        from pyramid.view import forbidden_view_config
        return forbidden_view_config(**kw)

    def test_ctor(self):
        inst = self._makeOne(attr='attr', path_info='path_info')
        self.assertEqual(inst.__dict__,
                         {'attr':'attr', 'path_info':'path_info'})

    def test_it_function(self):
        def view(request): pass
        decorator = self._makeOne(attr='attr', renderer='renderer')
        venusian = DummyVenusian()
        decorator.venusian = venusian
        wrapped = decorator(view)
        self.assertTrue(wrapped is view)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(
            settings, 
            [{'attr': 'attr', 'venusian': venusian, 
              'renderer': 'renderer', '_info': 'codeinfo', 'view': None}]
            )

    def test_it_class(self):
        decorator = self._makeOne()
        venusian = DummyVenusian()
        decorator.venusian = venusian
        decorator.venusian.info.scope = 'class'
        class view(object): pass
        wrapped = decorator(view)
        self.assertTrue(wrapped is view)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        self.assertEqual(len(settings[0]), 4)
        self.assertEqual(settings[0]['venusian'], venusian)
        self.assertEqual(settings[0]['view'], None) # comes from call_venusian
        self.assertEqual(settings[0]['attr'], 'view')
        self.assertEqual(settings[0]['_info'], 'codeinfo')
        
class RenderViewToResponseTests(BaseTest, unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from pyramid.view import render_view_to_response
        return render_view_to_response(*arg, **kw)
    
    def test_call_no_view_registered(self):
        request = self._makeRequest()
        context = self._makeContext()
        result = self._callFUT(context, request, name='notregistered')
        self.assertEqual(result, None)

    def test_call_no_registry_on_request(self):
        request = self._makeRequest()
        del request.registry
        context = self._makeContext()
        result = self._callFUT(context, request, name='notregistered')
        self.assertEqual(result, None)

    def test_call_view_registered_secure(self):
        request = self._makeRequest()
        context = self._makeContext()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(request.registry, view, 'registered')
        response = self._callFUT(context, request, name='registered',
                                 secure=True)
        self.assertEqual(response.status, '200 OK')

    def test_call_view_registered_insecure_no_call_permissive(self):
        context = self._makeContext()
        request = self._makeRequest()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(request.registry, view, 'registered')
        response = self._callFUT(context, request, name='registered',
                                 secure=False)
        self.assertEqual(response.status, '200 OK')

    def test_call_view_registered_insecure_with_call_permissive(self):
        context = self._makeContext()
        request = self._makeRequest()
        response = DummyResponse()
        view = make_view(response)
        def anotherview(context, request):
            return DummyResponse('anotherview')
        view.__call_permissive__ = anotherview
        self._registerView(request.registry, view, 'registered')
        response = self._callFUT(context, request, name='registered',
                                 secure=False)
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.app_iter, ['anotherview'])

class RenderViewToIterableTests(BaseTest, unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from pyramid.view import render_view_to_iterable
        return render_view_to_iterable(*arg, **kw)
    
    def test_call_no_view_registered(self):
        request = self._makeRequest()
        context = self._makeContext()
        result = self._callFUT(context, request, name='notregistered')
        self.assertEqual(result, None)

    def test_call_view_registered_secure(self):
        request = self._makeRequest()
        context = self._makeContext()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(request.registry, view, 'registered')
        iterable = self._callFUT(context, request, name='registered',
                                 secure=True)
        self.assertEqual(iterable, ())

    def test_call_view_registered_insecure_no_call_permissive(self):
        context = self._makeContext()
        request = self._makeRequest()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(request.registry, view, 'registered')
        iterable = self._callFUT(context, request, name='registered',
                                 secure=False)
        self.assertEqual(iterable, ())

    def test_call_view_registered_insecure_with_call_permissive(self):
        context = self._makeContext()
        request = self._makeRequest()
        response = DummyResponse()
        view = make_view(response)
        def anotherview(context, request):
            return DummyResponse(b'anotherview')
        view.__call_permissive__ = anotherview
        self._registerView(request.registry, view, 'registered')
        iterable = self._callFUT(context, request, name='registered',
                                 secure=False)
        self.assertEqual(iterable, [b'anotherview'])

    def test_verify_output_bytestring(self):
        from pyramid.request import Request
        from pyramid.config import Configurator
        from pyramid.view import render_view
        from webob.compat import text_type
        config = Configurator(settings={})
        def view(request):
            request.response.text = text_type('<body></body>')
            return request.response

        config.add_view(name='test', view=view)
        config.commit()

        r = Request({})
        r.registry = config.registry
        self.assertEqual(render_view(object(), r, 'test'), b'<body></body>')

    def test_call_request_has_no_registry(self):
        request = self._makeRequest()
        del request.registry
        registry = self.config.registry
        context = self._makeContext()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(registry, view, 'registered')
        iterable = self._callFUT(context, request, name='registered',
                                 secure=True)
        self.assertEqual(iterable, ())

class RenderViewTests(BaseTest, unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from pyramid.view import render_view
        return render_view(*arg, **kw)
    
    def test_call_no_view_registered(self):
        request = self._makeRequest()
        context = self._makeContext()
        result = self._callFUT(context, request, name='notregistered')
        self.assertEqual(result, None)

    def test_call_view_registered_secure(self):
        request = self._makeRequest()
        context = self._makeContext()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(request.registry, view, 'registered')
        s = self._callFUT(context, request, name='registered', secure=True)
        self.assertEqual(s, b'')

    def test_call_view_registered_insecure_no_call_permissive(self):
        context = self._makeContext()
        request = self._makeRequest()
        response = DummyResponse()
        view = make_view(response)
        self._registerView(request.registry, view, 'registered')
        s = self._callFUT(context, request, name='registered', secure=False)
        self.assertEqual(s, b'')

    def test_call_view_registered_insecure_with_call_permissive(self):
        context = self._makeContext()
        request = self._makeRequest()
        response = DummyResponse()
        view = make_view(response)
        def anotherview(context, request):
            return DummyResponse(b'anotherview')
        view.__call_permissive__ = anotherview
        self._registerView(request.registry, view, 'registered')
        s = self._callFUT(context, request, name='registered', secure=False)
        self.assertEqual(s, b'anotherview')

class TestViewConfigDecorator(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _getTargetClass(self):
        from pyramid.view import view_config
        return view_config

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def test_create_defaults(self):
        decorator = self._makeOne()
        self.assertEqual(decorator.__dict__, {})

    def test_create_context_trumps_for(self):
        decorator = self._makeOne(context='123', for_='456')
        self.assertEqual(decorator.context, '123')

    def test_create_for_trumps_context_None(self):
        decorator = self._makeOne(context=None, for_='456')
        self.assertEqual(decorator.context, '456')
        
    def test_create_nondefaults(self):
        decorator = self._makeOne(
            name=None, request_type=None, for_=None,
            permission='foo', mapper='mapper',
            decorator='decorator', match_param='match_param'
            )
        self.assertEqual(decorator.name, None)
        self.assertEqual(decorator.request_type, None)
        self.assertEqual(decorator.context, None)
        self.assertEqual(decorator.permission, 'foo')
        self.assertEqual(decorator.mapper, 'mapper')
        self.assertEqual(decorator.decorator, 'decorator')
        self.assertEqual(decorator.match_param, 'match_param')

    def test_create_with_other_predicates(self):
        decorator = self._makeOne(foo=1)
        self.assertEqual(decorator.foo, 1)

    def test_create_decorator_tuple(self):
        decorator = self._makeOne(decorator=('decorator1', 'decorator2'))
        self.assertEqual(decorator.decorator, ('decorator1', 'decorator2'))
        
    def test_call_function(self):
        decorator = self._makeOne()
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(): pass
        wrapped = decorator(foo)
        self.assertTrue(wrapped is foo)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        self.assertEqual(len(settings), 1)
        self.assertEqual(len(settings[0]), 3)
        self.assertEqual(settings[0]['venusian'], venusian)
        self.assertEqual(settings[0]['view'], None) # comes from call_venusian
        self.assertEqual(settings[0]['_info'], 'codeinfo')

    def test_call_class(self):
        decorator = self._makeOne()
        venusian = DummyVenusian()
        decorator.venusian = venusian
        decorator.venusian.info.scope = 'class'
        class foo(object): pass
        wrapped = decorator(foo)
        self.assertTrue(wrapped is foo)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        self.assertEqual(len(settings[0]), 4)
        self.assertEqual(settings[0]['venusian'], venusian)
        self.assertEqual(settings[0]['view'], None) # comes from call_venusian
        self.assertEqual(settings[0]['attr'], 'foo')
        self.assertEqual(settings[0]['_info'], 'codeinfo')

    def test_call_class_attr_already_set(self):
        decorator = self._makeOne(attr='abc')
        venusian = DummyVenusian()
        decorator.venusian = venusian
        decorator.venusian.info.scope = 'class'
        class foo(object): pass
        wrapped = decorator(foo)
        self.assertTrue(wrapped is foo)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        self.assertEqual(len(settings[0]), 4)
        self.assertEqual(settings[0]['venusian'], venusian)
        self.assertEqual(settings[0]['view'], None) # comes from call_venusian
        self.assertEqual(settings[0]['attr'], 'abc')
        self.assertEqual(settings[0]['_info'], 'codeinfo')

    def test_stacking(self):
        decorator1 = self._makeOne(name='1')
        venusian1 = DummyVenusian()
        decorator1.venusian = venusian1
        venusian2 = DummyVenusian()
        decorator2 = self._makeOne(name='2')
        decorator2.venusian = venusian2
        def foo(): pass
        wrapped1 = decorator1(foo)
        wrapped2 = decorator2(wrapped1)
        self.assertTrue(wrapped1 is foo)
        self.assertTrue(wrapped2 is foo)
        config1 = call_venusian(venusian1)
        self.assertEqual(len(config1.settings), 1)
        self.assertEqual(config1.settings[0]['name'], '1')
        config2 = call_venusian(venusian2)
        self.assertEqual(len(config2.settings), 1)
        self.assertEqual(config2.settings[0]['name'], '2')

    def test_call_as_method(self):
        decorator = self._makeOne()
        venusian = DummyVenusian()
        decorator.venusian = venusian
        decorator.venusian.info.scope = 'class'
        def foo(self): pass
        def bar(self): pass
        class foo(object):
            foomethod = decorator(foo)
            barmethod = decorator(bar)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 2)
        self.assertEqual(settings[0]['attr'], 'foo')
        self.assertEqual(settings[1]['attr'], 'bar')

    def test_with_custom_predicates(self):
        decorator = self._makeOne(custom_predicates=(1,))
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(context, request): pass
        decorated = decorator(foo)
        self.assertTrue(decorated is foo)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(settings[0]['custom_predicates'], (1,))

    def test_call_with_renderer_string(self):
        import pyramid.tests
        decorator = self._makeOne(renderer='fixtures/minimal.pt')
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(): pass
        wrapped = decorator(foo)
        self.assertTrue(wrapped is foo)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        renderer = settings[0]['renderer']
        self.assertEqual(renderer, 'fixtures/minimal.pt')
        self.assertEqual(config.pkg, pyramid.tests)

    def test_call_with_renderer_dict(self):
        import pyramid.tests
        decorator = self._makeOne(renderer={'a':1})
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(): pass
        wrapped = decorator(foo)
        self.assertTrue(wrapped is foo)
        config = call_venusian(venusian)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        self.assertEqual(settings[0]['renderer'], {'a':1})
        self.assertEqual(config.pkg, pyramid.tests)

    def test_call_with_renderer_IRendererInfo(self):
        import pyramid.tests
        from pyramid.interfaces import IRendererInfo
        @implementer(IRendererInfo)
        class DummyRendererHelper(object):
            pass
        renderer_helper = DummyRendererHelper()
        decorator = self._makeOne(renderer=renderer_helper)
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(): pass
        wrapped = decorator(foo)
        self.assertTrue(wrapped is foo)
        context = DummyVenusianContext()
        config = call_venusian(venusian, context)
        settings = config.settings
        self.assertEqual(len(settings), 1)
        renderer = settings[0]['renderer']
        self.assertTrue(renderer is renderer_helper)
        self.assertEqual(config.pkg, pyramid.tests)

    def test_call_withdepth(self):
        decorator = self._makeOne(_depth=1)
        venusian = DummyVenusian()
        decorator.venusian = venusian
        def foo(): pass
        decorator(foo)
        self.assertEqual(venusian.depth, 2)

class Test_append_slash_notfound_view(BaseTest, unittest.TestCase):
    def _callFUT(self, context, request):
        from pyramid.view import append_slash_notfound_view
        return append_slash_notfound_view(context, request)

    def _registerMapper(self, reg, match=True):
        from pyramid.interfaces import IRoutesMapper
        class DummyRoute(object):
            def __init__(self, val):
                self.val = val
            def match(self, path):
                return self.val
        class DummyMapper(object):
            def __init__(self):
                self.routelist = [ DummyRoute(match) ]
            def get_routes(self):
                return self.routelist
        mapper = DummyMapper()
        reg.registerUtility(mapper, IRoutesMapper)
        return mapper

    def test_context_is_not_exception(self):
        request = self._makeRequest(PATH_INFO='/abc')
        request.exception = ExceptionResponse()
        context = DummyContext()
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '404 Not Found')
        self.assertEqual(response.app_iter, ['Not Found'])

    def test_no_mapper(self):
        request = self._makeRequest(PATH_INFO='/abc')
        context = ExceptionResponse()
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '404 Not Found')

    def test_no_path(self):
        request = self._makeRequest()
        context = ExceptionResponse()
        self._registerMapper(request.registry, True)
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '404 Not Found')

    def test_mapper_path_already_slash_ending(self):
        request = self._makeRequest(PATH_INFO='/abc/')
        context = ExceptionResponse()
        self._registerMapper(request.registry, True)
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '404 Not Found')

    def test_no_route_matches(self):
        request = self._makeRequest(PATH_INFO='/abc')
        context = ExceptionResponse()
        mapper = self._registerMapper(request.registry, True)
        mapper.routelist[0].val = None
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '404 Not Found')

    def test_matches(self):
        request = self._makeRequest(PATH_INFO='/abc')
        context = ExceptionResponse()
        self._registerMapper(request.registry, True)
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '302 Found')
        self.assertEqual(response.location, '/abc/')

    def test_matches_with_script_name(self):
        request = self._makeRequest(PATH_INFO='/abc', SCRIPT_NAME='/foo')
        context = ExceptionResponse()
        self._registerMapper(request.registry, True)
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '302 Found')
        self.assertEqual(response.location, '/foo/abc/')

    def test_with_query_string(self):
        request = self._makeRequest(PATH_INFO='/abc', QUERY_STRING='a=1&b=2')
        context = ExceptionResponse()
        self._registerMapper(request.registry, True)
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '302 Found')
        self.assertEqual(response.location, '/abc/?a=1&b=2')

class TestAppendSlashNotFoundViewFactory(BaseTest, unittest.TestCase):
    def _makeOne(self, notfound_view):
        from pyramid.view import AppendSlashNotFoundViewFactory
        return AppendSlashNotFoundViewFactory(notfound_view)
    
    def test_custom_notfound_view(self):
        request = self._makeRequest(PATH_INFO='/abc')
        context = ExceptionResponse()
        def custom_notfound(context, request):
            return 'OK'
        view = self._makeOne(custom_notfound)
        response = view(context, request)
        self.assertEqual(response, 'OK')

class Test_default_exceptionresponse_view(unittest.TestCase):
    def _callFUT(self, context, request):
        from pyramid.view import default_exceptionresponse_view
        return default_exceptionresponse_view(context, request)

    def test_is_exception(self):
        context = Exception()
        result = self._callFUT(context, None)
        self.assertTrue(result is context)

    def test_is_not_exception_context_is_false_still_chose(self):
        request = DummyRequest()
        request.exception = 0
        result = self._callFUT(None, request)
        self.assertTrue(result is None)

    def test_is_not_exception_no_request_exception(self):
        context = object()
        request = DummyRequest()
        request.exception = None
        result = self._callFUT(context, request)
        self.assertTrue(result is context)

    def test_is_not_exception_request_exception(self):
        context = object()
        request = DummyRequest()
        request.exception = 'abc'
        result = self._callFUT(context, request)
        self.assertEqual(result, 'abc')

class Test_view_defaults(unittest.TestCase):
    def test_it(self):
        from pyramid.view import view_defaults
        @view_defaults(route_name='abc', renderer='def')
        class Foo(object): pass
        self.assertEqual(Foo.__view_defaults__['route_name'],'abc')
        self.assertEqual(Foo.__view_defaults__['renderer'],'def')

    def test_it_inheritance_not_overridden(self):
        from pyramid.view import view_defaults
        @view_defaults(route_name='abc', renderer='def')
        class Foo(object): pass
        class Bar(Foo): pass
        self.assertEqual(Bar.__view_defaults__['route_name'],'abc')
        self.assertEqual(Bar.__view_defaults__['renderer'],'def')

    def test_it_inheritance_overriden(self):
        from pyramid.view import view_defaults
        @view_defaults(route_name='abc', renderer='def')
        class Foo(object): pass
        @view_defaults(route_name='ghi')
        class Bar(Foo): pass
        self.assertEqual(Bar.__view_defaults__['route_name'],'ghi')
        self.assertFalse('renderer' in Bar.__view_defaults__)

    def test_it_inheritance_overriden_empty(self):
        from pyramid.view import view_defaults
        @view_defaults(route_name='abc', renderer='def')
        class Foo(object): pass
        @view_defaults()
        class Bar(Foo): pass
        self.assertEqual(Bar.__view_defaults__, {})

class ExceptionResponse(Exception):
    status = '404 Not Found'
    app_iter = ['Not Found']
    headerlist = []

class DummyContext:
    pass

def make_view(response):
    def view(context, request):
        return response
    return view

class DummyRequest:
    exception = None

    def __init__(self, environ=None):
        if environ is None:
            environ = {}
        self.environ = environ
        
from pyramid.interfaces import IResponse

@implementer(IResponse)
class DummyResponse(object):
    headerlist = ()
    app_iter = ()
    status = '200 OK'
    environ = None
    def __init__(self, body=None):
        if body is None:
            self.app_iter = ()
        else:
            self.app_iter = [body]

from zope.interface import Interface
class IContext(Interface):
    pass

class DummyVenusianInfo(object):
    scope = 'notaclass'
    module = sys.modules['pyramid.tests']
    codeinfo = 'codeinfo'

class DummyVenusian(object):
    def __init__(self, info=None):
        if info is None:
            info = DummyVenusianInfo()
        self.info = info
        self.attachments = []

    def attach(self, wrapped, callback, category=None, depth=1):
        self.attachments.append((wrapped, callback, category))
        self.depth = depth
        return self.info

class DummyRegistry(object):
    pass

class DummyConfig(object):
    def __init__(self):
        self.settings = []
        self.registry = DummyRegistry()

    def add_view(self, **kw):
        self.settings.append(kw)

    add_notfound_view = add_forbidden_view = add_view

    def with_package(self, pkg):
        self.pkg = pkg
        return self

class DummyVenusianContext(object):
    def __init__(self):
        self.config = DummyConfig()
        
def call_venusian(venusian, context=None):
    if context is None:
        context = DummyVenusianContext()
    for wrapped, callback, category in venusian.attachments:
        callback(context, None, None)
    return context.config

