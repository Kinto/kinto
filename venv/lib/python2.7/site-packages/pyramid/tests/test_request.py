import unittest
from pyramid import testing

from pyramid.compat import (
    PY3,
    text_,
    bytes_,
    native_,
    )
from pyramid.security import (
    AuthenticationAPIMixin,
    AuthorizationAPIMixin,
    )

class TestRequest(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _getTargetClass(self):
        from pyramid.request import Request
        return Request

    def _makeOne(self, environ=None):
        if environ is None:
            environ = {}
        return self._getTargetClass()(environ)

    def _registerResourceURL(self):
        from pyramid.interfaces import IResourceURL
        from zope.interface import Interface
        class DummyResourceURL(object):
            def __init__(self, context, request):
                self.physical_path = '/context/'
                self.virtual_path = '/context/'
        self.config.registry.registerAdapter(
            DummyResourceURL, (Interface, Interface),
            IResourceURL)

    def test_class_conforms_to_IRequest(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IRequest
        verifyClass(IRequest, self._getTargetClass())

    def test_instance_conforms_to_IRequest(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IRequest
        verifyObject(IRequest, self._makeOne())

    def test_ResponseClass_is_pyramid_Response(self):
        from pyramid.response import Response
        cls = self._getTargetClass()
        self.assertEqual(cls.ResponseClass, Response)

    def test_implements_security_apis(self):
        apis = (AuthenticationAPIMixin, AuthorizationAPIMixin)
        r = self._makeOne()
        self.assertTrue(isinstance(r, apis))

    def test_charset_defaults_to_utf8(self):
        r = self._makeOne({'PATH_INFO':'/'})
        self.assertEqual(r.charset, 'UTF-8')

    def test_exception_defaults_to_None(self):
        r = self._makeOne({'PATH_INFO':'/'})
        self.assertEqual(r.exception, None)

    def test_matchdict_defaults_to_None(self):
        r = self._makeOne({'PATH_INFO':'/'})
        self.assertEqual(r.matchdict, None)

    def test_matched_route_defaults_to_None(self):
        r = self._makeOne({'PATH_INFO':'/'})
        self.assertEqual(r.matched_route, None)

    def test_params_decoded_from_utf_8_by_default(self):
        environ = {
            'PATH_INFO':'/',
            'QUERY_STRING':'la=La%20Pe%C3%B1a'
            }
        request = self._makeOne(environ)
        request.charset = None
        self.assertEqual(request.GET['la'], text_(b'La Pe\xf1a'))

    def test_tmpl_context(self):
        from pyramid.request import TemplateContext
        inst = self._makeOne()
        result = inst.tmpl_context
        self.assertEqual(result.__class__, TemplateContext)

    def test_session_configured(self):
        from pyramid.interfaces import ISessionFactory
        inst = self._makeOne()
        def factory(request):
            return 'orangejuice'
        self.config.registry.registerUtility(factory, ISessionFactory)
        inst.registry = self.config.registry
        self.assertEqual(inst.session, 'orangejuice')
        self.assertEqual(inst.__dict__['session'], 'orangejuice')

    def test_session_not_configured(self):
        inst = self._makeOne()
        inst.registry = self.config.registry
        self.assertRaises(AttributeError, getattr, inst, 'session')

    def test_setattr_and_getattr_dotnotation(self):
        inst = self._makeOne()
        inst.foo = 1
        self.assertEqual(inst.foo, 1)

    def test_setattr_and_getattr(self):
        environ = {}
        inst = self._makeOne(environ)
        setattr(inst, 'bar', 1)
        self.assertEqual(getattr(inst, 'bar'), 1)
        self.assertEqual(environ, {}) # make sure we're not using adhoc attrs

    def test_add_response_callback(self):
        inst = self._makeOne()
        self.assertEqual(inst.response_callbacks, ())
        def callback(request, response):
            """ """
        inst.add_response_callback(callback)
        self.assertEqual(inst.response_callbacks, [callback])
        inst.add_response_callback(callback)
        self.assertEqual(inst.response_callbacks, [callback, callback])

    def test__process_response_callbacks(self):
        inst = self._makeOne()
        def callback1(request, response):
            request.called1 = True
            response.called1 = True
        def callback2(request, response):
            request.called2  = True
            response.called2 = True
        inst.response_callbacks = [callback1, callback2]
        response = DummyResponse()
        inst._process_response_callbacks(response)
        self.assertEqual(inst.called1, True)
        self.assertEqual(inst.called2, True)
        self.assertEqual(response.called1, True)
        self.assertEqual(response.called2, True)
        self.assertEqual(inst.response_callbacks, [])

    def test_add_finished_callback(self):
        inst = self._makeOne()
        self.assertEqual(inst.finished_callbacks, ())
        def callback(request):
            """ """
        inst.add_finished_callback(callback)
        self.assertEqual(inst.finished_callbacks, [callback])
        inst.add_finished_callback(callback)
        self.assertEqual(inst.finished_callbacks, [callback, callback])

    def test__process_finished_callbacks(self):
        inst = self._makeOne()
        def callback1(request):
            request.called1 = True
        def callback2(request):
            request.called2  = True
        inst.finished_callbacks = [callback1, callback2]
        inst._process_finished_callbacks()
        self.assertEqual(inst.called1, True)
        self.assertEqual(inst.called2, True)
        self.assertEqual(inst.finished_callbacks, [])

    def test_resource_url(self):
        self._registerResourceURL()
        environ = {
            'PATH_INFO':'/',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            'wsgi.url_scheme':'http',
            }
        inst = self._makeOne(environ)
        root = DummyContext()
        result = inst.resource_url(root)
        self.assertEqual(result, 'http://example.com/context/')

    def test_route_url(self):
        environ = {
            'PATH_INFO':'/',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'5432',
            'QUERY_STRING':'la=La%20Pe%C3%B1a',
            'wsgi.url_scheme':'http',
            }
        from pyramid.interfaces import IRoutesMapper
        inst = self._makeOne(environ)
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        self.config.registry.registerUtility(mapper, IRoutesMapper)
        result = inst.route_url('flub', 'extra1', 'extra2',
                                a=1, b=2, c=3, _query={'a':1},
                                _anchor=text_("foo"))
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3/extra1/extra2?a=1#foo')

    def test_route_path(self):
        environ = {
            'PATH_INFO':'/',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'5432',
            'QUERY_STRING':'la=La%20Pe%C3%B1a',
            'wsgi.url_scheme':'http',
            }
        from pyramid.interfaces import IRoutesMapper
        inst = self._makeOne(environ)
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        self.config.registry.registerUtility(mapper, IRoutesMapper)
        result = inst.route_path('flub', 'extra1', 'extra2',
                                a=1, b=2, c=3, _query={'a':1},
                                _anchor=text_("foo"))
        self.assertEqual(result, '/1/2/3/extra1/extra2?a=1#foo')

    def test_static_url(self):
        from pyramid.interfaces import IStaticURLInfo
        environ = {
            'PATH_INFO':'/',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'5432',
            'QUERY_STRING':'',
            'wsgi.url_scheme':'http',
            }
        request = self._makeOne(environ)
        info = DummyStaticURLInfo('abc')
        self.config.registry.registerUtility(info, IStaticURLInfo)
        result = request.static_url('pyramid.tests:static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request, {}) )

    def test_is_response_false(self):
        request = self._makeOne()
        request.registry = self.config.registry
        self.assertEqual(request.is_response('abc'), False)

    def test_is_response_true_ob_is_pyramid_response(self):
        from pyramid.response import Response
        r = Response('hello')
        request = self._makeOne()
        request.registry = self.config.registry
        self.assertEqual(request.is_response(r), True)

    def test_is_response_false_adapter_is_not_self(self):
        from pyramid.interfaces import IResponse
        request = self._makeOne()
        request.registry = self.config.registry
        def adapter(ob):
            return object()
        class Foo(object):
            pass
        foo = Foo()
        request.registry.registerAdapter(adapter, (Foo,), IResponse)
        self.assertEqual(request.is_response(foo), False)
        
    def test_is_response_adapter_true(self):
        from pyramid.interfaces import IResponse
        request = self._makeOne()
        request.registry = self.config.registry
        class Foo(object):
            pass
        foo = Foo()
        def adapter(ob):
            return ob
        request.registry.registerAdapter(adapter, (Foo,), IResponse)
        self.assertEqual(request.is_response(foo), True)

    def test_json_body_invalid_json(self):
        request = self._makeOne({'REQUEST_METHOD':'POST'})
        request.body = b'{'
        self.assertRaises(ValueError, getattr, request, 'json_body')
        
    def test_json_body_valid_json(self):
        request = self._makeOne({'REQUEST_METHOD':'POST'})
        request.body = b'{"a":1}'
        self.assertEqual(request.json_body, {'a':1})

    def test_json_body_alternate_charset(self):
        import json
        request = self._makeOne({'REQUEST_METHOD':'POST'})
        inp = text_(
            b'/\xe6\xb5\x81\xe8\xa1\x8c\xe8\xb6\x8b\xe5\x8a\xbf',
            'utf-8'
            )
        if PY3: # pragma: no cover
            body = bytes(json.dumps({'a':inp}), 'utf-16')
        else:
            body = json.dumps({'a':inp}).decode('utf-8').encode('utf-16')
        request.body = body
        request.content_type = 'application/json; charset=utf-16'
        self.assertEqual(request.json_body, {'a':inp})

    def test_json_body_GET_request(self):
        request = self._makeOne({'REQUEST_METHOD':'GET'})
        self.assertRaises(ValueError, getattr, request, 'json_body')

    def test_set_property(self):
        request = self._makeOne()
        opts = [2, 1]
        def connect(obj):
            return opts.pop()
        request.set_property(connect, name='db')
        self.assertEqual(1, request.db)
        self.assertEqual(2, request.db)

    def test_set_property_reify(self):
        request = self._makeOne()
        opts = [2, 1]
        def connect(obj):
            return opts.pop()
        request.set_property(connect, name='db', reify=True)
        self.assertEqual(1, request.db)
        self.assertEqual(1, request.db)

class Test_route_request_iface(unittest.TestCase):
    def _callFUT(self, name):
        from pyramid.request import route_request_iface
        return route_request_iface(name)

    def test_it(self):
        iface = self._callFUT('routename')
        self.assertEqual(iface.__name__, 'routename_IRequest')
        self.assertTrue(hasattr(iface, 'combined'))
        self.assertEqual(iface.combined.__name__, 'routename_combined_IRequest')

    def test_it_routename_with_spaces(self):
        #  see https://github.com/Pylons/pyramid/issues/232
        iface = self._callFUT('routename with spaces')
        self.assertEqual(iface.__name__, 'routename with spaces_IRequest')
        self.assertTrue(hasattr(iface, 'combined'))
        self.assertEqual(iface.combined.__name__,
                         'routename with spaces_combined_IRequest')
        

class Test_add_global_response_headers(unittest.TestCase):
    def _callFUT(self, request, headerlist):
        from pyramid.request import add_global_response_headers
        return add_global_response_headers(request, headerlist)

    def test_it(self):
        request = DummyRequest()
        response = DummyResponse()
        self._callFUT(request, [('c', 1)])
        self.assertEqual(len(request.response_callbacks), 1)
        request.response_callbacks[0](None, response)
        self.assertEqual(response.headerlist,  [('c', 1)] )

class Test_call_app_with_subpath_as_path_info(unittest.TestCase):
    def _callFUT(self, request, app):
        from pyramid.request import call_app_with_subpath_as_path_info
        return call_app_with_subpath_as_path_info(request, app)

    def test_it_all_request_and_environment_data_missing(self):
        request = DummyRequest({})
        response = self._callFUT(request, 'app')
        self.assertTrue(request.copied)
        self.assertEqual(response, 'app')
        self.assertEqual(request.environ['SCRIPT_NAME'], '')
        self.assertEqual(request.environ['PATH_INFO'], '/')

    def test_it_with_subpath_and_path_info(self):
        request = DummyRequest({'PATH_INFO':'/hello'})
        request.subpath = ('hello',)
        response = self._callFUT(request, 'app')
        self.assertTrue(request.copied)
        self.assertEqual(response, 'app')
        self.assertEqual(request.environ['SCRIPT_NAME'], '')
        self.assertEqual(request.environ['PATH_INFO'], '/hello')

    def test_it_with_subpath_and_path_info_path_info_endswith_slash(self):
        request = DummyRequest({'PATH_INFO':'/hello/'})
        request.subpath = ('hello',)
        response = self._callFUT(request, 'app')
        self.assertTrue(request.copied)
        self.assertEqual(response, 'app')
        self.assertEqual(request.environ['SCRIPT_NAME'], '')
        self.assertEqual(request.environ['PATH_INFO'], '/hello/')

    def test_it_with_subpath_and_path_info_extra_script_name(self):
        request = DummyRequest({'PATH_INFO':'/hello', 'SCRIPT_NAME':'/script'})
        request.subpath = ('hello',)
        response = self._callFUT(request, 'app')
        self.assertTrue(request.copied)
        self.assertEqual(response, 'app')
        self.assertEqual(request.environ['SCRIPT_NAME'], '/script')
        self.assertEqual(request.environ['PATH_INFO'], '/hello')

    def test_it_with_extra_slashes_in_path_info(self):
        request = DummyRequest({'PATH_INFO':'//hello/',
                                'SCRIPT_NAME':'/script'})
        request.subpath = ('hello',)
        response = self._callFUT(request, 'app')
        self.assertTrue(request.copied)
        self.assertEqual(response, 'app')
        self.assertEqual(request.environ['SCRIPT_NAME'], '/script')
        self.assertEqual(request.environ['PATH_INFO'], '/hello/')

    def test_subpath_path_info_and_script_name_have_utf8(self):
        encoded = native_(text_(b'La Pe\xc3\xb1a'))
        decoded = text_(bytes_(encoded), 'utf-8')
        request = DummyRequest({'PATH_INFO':'/' + encoded,
                                'SCRIPT_NAME':'/' + encoded})
        request.subpath = (decoded, )
        response = self._callFUT(request, 'app')
        self.assertTrue(request.copied)
        self.assertEqual(response, 'app')
        self.assertEqual(request.environ['SCRIPT_NAME'], '/' + encoded)
        self.assertEqual(request.environ['PATH_INFO'], '/' + encoded)

class DummyRequest:
    def __init__(self, environ=None):
        if environ is None:
            environ = {}
        self.environ = environ

    def add_response_callback(self, callback):
        self.response_callbacks = [callback]

    def get_response(self, app):
        return app

    def copy(self):
        self.copied = True
        return self

class DummyResponse:
    def __init__(self):
        self.headerlist = []


class DummyContext:
    pass

class DummyRoutesMapper:
    raise_exc = None
    def __init__(self, route=None, raise_exc=False):
        self.route = route

    def get_route(self, route_name):
        return self.route

class DummyRoute:
    pregenerator = None
    def __init__(self, result='/1/2/3'):
        self.result = result

    def generate(self, kw):
        self.kw = kw
        return self.result

class DummyStaticURLInfo:
    def __init__(self, result):
        self.result = result

    def generate(self, path, request, **kw):
        self.args = path, request, kw
        return self.result
