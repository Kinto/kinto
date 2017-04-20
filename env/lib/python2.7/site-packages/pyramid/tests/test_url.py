import os
import unittest
import warnings

from pyramid import testing

from pyramid.compat import (
    text_,
    WIN,
    )

class TestURLMethodsMixin(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def _makeOne(self, environ=None):
        from pyramid.url import URLMethodsMixin
        if environ is None:
            environ = {}
        class Request(URLMethodsMixin):
            application_url = 'http://example.com:5432'
            script_name = ''
            def __init__(self, environ):
                self.environ = environ
        request = Request(environ)
        request.registry = self.config.registry
        return request

    def _registerContextURL(self, reg):
        with warnings.catch_warnings(record=True):
            from pyramid.interfaces import IContextURL
        from zope.interface import Interface
        class DummyContextURL(object):
            def __init__(self, context, request):
                pass
            def __call__(self):
                return 'http://example.com/context/'
        reg.registerAdapter(DummyContextURL, (Interface, Interface),
                            IContextURL)

    def _registerResourceURL(self, reg):
        from pyramid.interfaces import IResourceURL
        from zope.interface import Interface
        class DummyResourceURL(object):
            physical_path = '/context/'
            virtual_path = '/context/'
            def __init__(self, context, request): pass
        reg.registerAdapter(DummyResourceURL, (Interface, Interface),
                            IResourceURL)
        return DummyResourceURL

    def test_resource_url_root_default(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_url(root)
        self.assertEqual(result, 'http://example.com:5432/context/')

    def test_resource_url_extra_args(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, 'this/theotherthing', 'that')
        self.assertEqual(
            result,
            'http://example.com:5432/context/this%2Ftheotherthing/that')

    def test_resource_url_unicode_in_element_names(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        uc = text_(b'La Pe\xc3\xb1a', 'utf-8')
        context = DummyContext()
        result = request.resource_url(context, uc)
        self.assertEqual(result,
                     'http://example.com:5432/context/La%20Pe%C3%B1a')

    def test_resource_url_at_sign_in_element_names(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, '@@myview')
        self.assertEqual(result,
                     'http://example.com:5432/context/@@myview')

    def test_resource_url_element_names_url_quoted(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, 'a b c')
        self.assertEqual(result, 'http://example.com:5432/context/a%20b%20c')

    def test_resource_url_with_query_str(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, 'a', query='(openlayers)')
        self.assertEqual(result,
            'http://example.com:5432/context/a?(openlayers)')

    def test_resource_url_with_query_dict(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        uc = text_(b'La Pe\xc3\xb1a', 'utf-8')
        result = request.resource_url(context, 'a', query={'a':uc})
        self.assertEqual(result,
                         'http://example.com:5432/context/a?a=La+Pe%C3%B1a')

    def test_resource_url_with_query_seq(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        uc = text_(b'La Pe\xc3\xb1a', 'utf-8')
        result = request.resource_url(context, 'a', query=[('a', 'hi there'),
                                                           ('b', uc)])
        self.assertEqual(result,
            'http://example.com:5432/context/a?a=hi+there&b=La+Pe%C3%B1a')

    def test_resource_url_with_query_empty(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, 'a', query=[])
        self.assertEqual(result,
            'http://example.com:5432/context/a')

    def test_resource_url_anchor_is_after_root_when_no_elements(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, anchor='a')
        self.assertEqual(result,
                         'http://example.com:5432/context/#a')

    def test_resource_url_anchor_is_after_elements_when_no_qs(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, 'a', anchor='b')
        self.assertEqual(result,
                         'http://example.com:5432/context/a#b')

    def test_resource_url_anchor_is_after_qs_when_qs_is_present(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, 'a', 
                                      query={'b':'c'}, anchor='d')
        self.assertEqual(result,
                         'http://example.com:5432/context/a?b=c#d')

    def test_resource_url_anchor_is_encoded_utf8_if_unicode(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        uc = text_(b'La Pe\xc3\xb1a', 'utf-8')
        result = request.resource_url(context, anchor=uc)
        self.assertEqual(result,
                         'http://example.com:5432/context/#La%20Pe%C3%B1a')

    def test_resource_url_anchor_is_urlencoded_safe(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        context = DummyContext()
        result = request.resource_url(context, anchor=' /#?&+')
        self.assertEqual(result,
                         'http://example.com:5432/context/#%20/%23?&+')

    def test_resource_url_no_IResourceURL_registered(self):
        # falls back to ResourceURL
        root = DummyContext()
        root.__name__ = ''
        root.__parent__ = None
        request = self._makeOne()
        request.environ = {}
        result = request.resource_url(root)
        self.assertEqual(result, 'http://example.com:5432/')

    def test_resource_url_no_registry_on_request(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        del request.registry
        root = DummyContext()
        result = request.resource_url(root)
        self.assertEqual(result, 'http://example.com:5432/context/')

    def test_resource_url_finds_IContextURL(self):
        request = self._makeOne()
        self._registerContextURL(request.registry)
        root = DummyContext()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            result = request.resource_url(root)
            self.assertEqual(len(w), 1)
        self.assertEqual(result, 'http://example.com/context/')
        
    def test_resource_url_with_app_url(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_url(root, app_url='http://somewhere.com')
        self.assertEqual(result, 'http://somewhere.com/context/')

    def test_resource_url_with_scheme(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_url(root, scheme='https')
        self.assertEqual(result, 'https://example.com/context/')

    def test_resource_url_with_host(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_url(root, host='someotherhost.com')
        self.assertEqual(result, 'http://someotherhost.com:8080/context/')

    def test_resource_url_with_port(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_url(root, port='8181')
        self.assertEqual(result, 'http://example.com:8181/context/')

    def test_resource_url_with_local_url(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        self._registerResourceURL(request.registry)
        root = DummyContext()
        def resource_url(req, info):
            self.assertEqual(req, request)
            self.assertEqual(info['virtual_path'], '/context/')
            self.assertEqual(info['physical_path'], '/context/')
            self.assertEqual(info['app_url'], 'http://example.com:5432')
            return 'http://example.com/contextabc/'
        root.__resource_url__ = resource_url
        result = request.resource_url(root)
        self.assertEqual(result, 'http://example.com/contextabc/')

    def test_resource_url_with_route_name_no_remainder_on_adapter(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # no virtual_path_tuple on adapter
        adapter.virtual_path = '/a/b/c/'
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(root, route_name='foo')
        self.assertEqual(result, 'http://example.com:5432/1/2/3')
        self.assertEqual(route.kw, {'traverse': ('', 'a', 'b', 'c', '')})

    def test_resource_url_with_route_name_remainder_on_adapter(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # virtual_path_tuple on adapter
        adapter.virtual_path_tuple = ('', 'a', 'b', 'c', '')
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(root, route_name='foo')
        self.assertEqual(result, 'http://example.com:5432/1/2/3')
        self.assertEqual(route.kw, {'traverse': ('', 'a', 'b', 'c', '')})

    def test_resource_url_with_route_name_and_app_url(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # virtual_path_tuple on adapter
        adapter.virtual_path_tuple = ('', 'a', 'b', 'c', '')
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(root, route_name='foo', app_url='app_url')
        self.assertEqual(result, 'app_url/1/2/3')
        self.assertEqual(route.kw, {'traverse': ('', 'a', 'b', 'c', '')})

    def test_resource_url_with_route_name_and_scheme_host_port_etc(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # virtual_path_tuple on adapter
        adapter.virtual_path_tuple = ('', 'a', 'b', 'c', '')
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(root, route_name='foo', scheme='scheme',
                                      host='host', port='port', query={'a':'1'},
                                      anchor='anchor')
        self.assertEqual(result, 'scheme://host:port/1/2/3?a=1#anchor')
        self.assertEqual(route.kw, {'traverse': ('', 'a', 'b', 'c', '')})

    def test_resource_url_with_route_name_and_route_kwargs(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # virtual_path_tuple on adapter
        adapter.virtual_path_tuple = ('', 'a', 'b', 'c', '')
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(
            root, route_name='foo', route_kw={'a':'1', 'b':'2'})
        self.assertEqual(result, 'http://example.com:5432/1/2/3')
        self.assertEqual(
            route.kw,
            {'traverse': ('', 'a', 'b', 'c', ''),
             'a':'1',
             'b':'2'}
            )

    def test_resource_url_with_route_name_and_elements(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # virtual_path_tuple on adapter
        adapter.virtual_path_tuple = ('', 'a', 'b', 'c', '')
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(root, 'e1', 'e2', route_name='foo')
        self.assertEqual(result,  'http://example.com:5432/1/2/3/e1/e2')
        self.assertEqual(route.kw, {'traverse': ('', 'a', 'b', 'c', '')})
        
    def test_resource_url_with_route_name_and_remainder_name(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'8080',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        adapter = self._registerResourceURL(request.registry)
        # virtual_path_tuple on adapter
        adapter.virtual_path_tuple = ('', 'a', 'b', 'c', '')
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        root = DummyContext()
        result = request.resource_url(root, route_name='foo',
                                      route_remainder_name='fred')
        self.assertEqual(result, 'http://example.com:5432/1/2/3')
        self.assertEqual(route.kw, {'fred': ('', 'a', 'b', 'c', '')})
        
    def test_resource_path(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_path(root)
        self.assertEqual(result, '/context/')

    def test_resource_path_kwarg(self):
        request = self._makeOne()
        self._registerResourceURL(request.registry)
        root = DummyContext()
        result = request.resource_path(root, anchor='abc')
        self.assertEqual(result, '/context/#abc')
        
    def test_route_url_with_elements(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', 'extra1', 'extra2')
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3/extra1/extra2')

    def test_route_url_with_elements_path_endswith_slash(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3/'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', 'extra1', 'extra2')
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3/extra1/extra2')

    def test_route_url_no_elements(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', a=1, b=2, c=3, _query={'a':1},
                                   _anchor=text_(b"foo"))
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3?a=1#foo')

    def test_route_url_with_anchor_binary(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _anchor=b"La Pe\xc3\xb1a")

        self.assertEqual(result,
                         'http://example.com:5432/1/2/3#La%20Pe%C3%B1a')

    def test_route_url_with_anchor_unicode(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        anchor = text_(b'La Pe\xc3\xb1a', 'utf-8')
        result = request.route_url('flub', _anchor=anchor)

        self.assertEqual(result,
                         'http://example.com:5432/1/2/3#La%20Pe%C3%B1a')

    def test_route_url_with_query(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _query={'q':'1'})
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3?q=1')

    def test_route_url_with_query_str(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _query='(openlayers)')
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3?(openlayers)')

    def test_route_url_with_empty_query(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _query={})
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3')

    def test_route_url_with_app_url(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _app_url='http://example2.com')
        self.assertEqual(result,
                         'http://example2.com/1/2/3')

    def test_route_url_with_host(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'5432',
            }
        request = self._makeOne(environ)
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _host='someotherhost.com')
        self.assertEqual(result,
                         'http://someotherhost.com:5432/1/2/3')

    def test_route_url_with_port(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'5432',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _port='8080')
        self.assertEqual(result,
                         'http://example.com:8080/1/2/3')

    def test_route_url_with_scheme(self):
        from pyramid.interfaces import IRoutesMapper
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_PORT':'5432',
            'SERVER_NAME':'example.com',
            }
        request = self._makeOne(environ)
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _scheme='https')
        self.assertEqual(result,
                         'https://example.com/1/2/3')
        
    def test_route_url_generation_error(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(raise_exc=KeyError)
        request.registry.registerUtility(mapper, IRoutesMapper)
        mapper.raise_exc = KeyError
        self.assertRaises(KeyError, request.route_url, 'flub', request, a=1)

    def test_route_url_generate_doesnt_receive_query_or_anchor(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        route = DummyRoute(result='')
        mapper = DummyRoutesMapper(route=route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', _query=dict(name='some_name'))
        self.assertEqual(route.kw, {}) # shouldnt have anchor/query
        self.assertEqual(result, 'http://example.com:5432?name=some_name')

    def test_route_url_with_pregenerator(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        route = DummyRoute(result='/1/2/3')
        def pregenerator(request, elements, kw):
            return ('a',), {'_app_url':'http://example2.com'}
        route.pregenerator = pregenerator
        mapper = DummyRoutesMapper(route=route)
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub')
        self.assertEqual(result,  'http://example2.com/1/2/3/a')
        self.assertEqual(route.kw, {}) # shouldnt have anchor/query

    def test_route_url_with_anchor_app_url_elements_and_query(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute(result='/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', 'element1',
                                   _app_url='http://example2.com',
                                   _anchor='anchor', _query={'q':'1'})
        self.assertEqual(result,
                         'http://example2.com/1/2/3/element1?q=1#anchor')

    def test_route_url_integration_with_real_request(self):
        # to try to replicate https://github.com/Pylons/pyramid/issues/213
        from pyramid.interfaces import IRoutesMapper
        from pyramid.request import Request
        request = Request.blank('/')
        request.registry = self.config.registry
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_url('flub', 'extra1', 'extra2')
        self.assertEqual(result,
                         'http://localhost/1/2/3/extra1/extra2')
        

    def test_current_route_url_current_request_has_no_route(self):
        request = self._makeOne()
        self.assertRaises(ValueError, request.current_route_url)

    def test_current_route_url_with_elements_query_and_anchor(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route=route)
        request.matched_route = route
        request.matchdict = {}
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.current_route_url('extra1', 'extra2', _query={'a':1},
                                           _anchor=text_(b"foo"))
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3/extra1/extra2?a=1#foo')

    def test_current_route_url_with_route_name(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route=route)
        request.matched_route = route
        request.matchdict = {}
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.current_route_url('extra1', 'extra2', _query={'a':1},
                                           _anchor=text_(b"foo"),
                                           _route_name='bar')
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3/extra1/extra2?a=1#foo')

    def test_current_route_url_with_request_query(self):
        from pyramid.interfaces import IRoutesMapper
        from webob.multidict import GetDict
        request = self._makeOne()
        request.GET = GetDict([('q', '123')], {})
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route=route)
        request.matched_route = route
        request.matchdict = {}
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.current_route_url()
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3?q=123')

    def test_current_route_url_with_request_query_duplicate_entries(self):
        from pyramid.interfaces import IRoutesMapper
        from webob.multidict import GetDict
        request = self._makeOne()
        request.GET = GetDict(
            [('q', '123'), ('b', '2'), ('b', '2'), ('q', '456')], {})
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route=route)
        request.matched_route = route
        request.matchdict = {}
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.current_route_url()
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3?q=123&b=2&b=2&q=456')

    def test_current_route_url_with_query_override(self):
        from pyramid.interfaces import IRoutesMapper
        from webob.multidict import GetDict
        request = self._makeOne()
        request.GET = GetDict([('q', '123')], {})
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route=route)
        request.matched_route = route
        request.matchdict = {}
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.current_route_url(_query={'a':1})
        self.assertEqual(result,
                         'http://example.com:5432/1/2/3?a=1')

    def test_current_route_path(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        route = DummyRoute('/1/2/3')
        mapper = DummyRoutesMapper(route=route)
        request.matched_route = route
        request.matchdict = {}
        request.script_name = '/script_name'
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.current_route_path('extra1', 'extra2', _query={'a':1},
                                            _anchor=text_(b"foo"))
        self.assertEqual(result, '/script_name/1/2/3/extra1/extra2?a=1#foo')

    def test_route_path_with_elements(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        request.script_name = ''
        result = request.route_path('flub', 'extra1', 'extra2',
                                    a=1, b=2, c=3, _query={'a':1},
                                    _anchor=text_(b"foo"))
        self.assertEqual(result, '/1/2/3/extra1/extra2?a=1#foo')

    def test_route_path_with_script_name(self):
        from pyramid.interfaces import IRoutesMapper
        request = self._makeOne()
        request.script_name = '/foo'
        mapper = DummyRoutesMapper(route=DummyRoute('/1/2/3'))
        request.registry.registerUtility(mapper, IRoutesMapper)
        result = request.route_path('flub', 'extra1', 'extra2',
                                    a=1, b=2, c=3, _query={'a':1},
                                    _anchor=text_(b"foo"))
        self.assertEqual(result, '/foo/1/2/3/extra1/extra2?a=1#foo')
        
    def test_static_url_staticurlinfo_notfound(self):
        request = self._makeOne()
        self.assertRaises(ValueError, request.static_url, 'static/foo.css')

    def test_static_url_abspath(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        info = DummyStaticURLInfo('abc')
        registry = request.registry
        registry.registerUtility(info, IStaticURLInfo)
        abspath = makeabs('static', 'foo.css')
        result = request.static_url(abspath)
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args, (makeabs('static', 'foo.css'), request, {}))
        request = self._makeOne()

    def test_static_url_found_rel(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        info = DummyStaticURLInfo('abc')
        request.registry.registerUtility(info, IStaticURLInfo)
        result = request.static_url('static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request, {}) )

    def test_static_url_abs(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        info = DummyStaticURLInfo('abc')
        request.registry.registerUtility(info, IStaticURLInfo)
        result = request.static_url('pyramid.tests:static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request, {}) )

    def test_static_url_found_abs_no_registry_on_request(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        registry = request.registry
        info = DummyStaticURLInfo('abc')
        registry.registerUtility(info, IStaticURLInfo)
        del request.registry
        result = request.static_url('pyramid.tests:static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request, {}) )

    def test_static_url_abspath_integration_with_staticurlinfo(self):
        from pyramid.interfaces import IStaticURLInfo
        from pyramid.config.views import StaticURLInfo
        info = StaticURLInfo()
        here = os.path.abspath(os.path.dirname(__file__))
        info.add(self.config, 'absstatic', here)
        request = self._makeOne()
        registry = request.registry
        registry.registerUtility(info, IStaticURLInfo)
        abspath = os.path.join(here, 'test_url.py')
        result = request.static_url(abspath)
        self.assertEqual(result,
                         'http://example.com:5432/absstatic/test_url.py')

    def test_static_url_noscheme_uses_scheme_from_request(self):
        from pyramid.interfaces import IStaticURLInfo
        from pyramid.config.views import StaticURLInfo
        info = StaticURLInfo()
        here = os.path.abspath(os.path.dirname(__file__))
        info.add(self.config, '//subdomain.example.com/static', here)
        request = self._makeOne({'wsgi.url_scheme': 'https'})
        registry = request.registry
        registry.registerUtility(info, IStaticURLInfo)
        abspath = os.path.join(here, 'test_url.py')
        result = request.static_url(abspath)
        self.assertEqual(result,
                         'https://subdomain.example.com/static/test_url.py')

    def test_static_path_abspath(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        request.script_name = '/foo'
        info = DummyStaticURLInfo('abc')
        registry = request.registry
        registry.registerUtility(info, IStaticURLInfo)
        abspath = makeabs('static', 'foo.css')
        result = request.static_path(abspath)
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args, (makeabs('static', 'foo.css'), request,
                                     {'_app_url':'/foo'})
                         )

    def test_static_path_found_rel(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        request.script_name = '/foo'
        info = DummyStaticURLInfo('abc')
        request.registry.registerUtility(info, IStaticURLInfo)
        result = request.static_path('static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request,
                          {'_app_url':'/foo'})
                         )

    def test_static_path_abs(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        request.script_name = '/foo'
        info = DummyStaticURLInfo('abc')
        request.registry.registerUtility(info, IStaticURLInfo)
        result = request.static_path('pyramid.tests:static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request,
                          {'_app_url':'/foo'})
                         )

    def test_static_path(self):
        from pyramid.interfaces import IStaticURLInfo
        request = self._makeOne()
        request.script_name = '/foo'
        info = DummyStaticURLInfo('abc')
        request.registry.registerUtility(info, IStaticURLInfo)
        result = request.static_path('static/foo.css')
        self.assertEqual(result, 'abc')
        self.assertEqual(info.args,
                         ('pyramid.tests:static/foo.css', request,
                          {'_app_url':'/foo'})
                         )

    def test_partial_application_url_with_http_host_default_port_http(self):
        environ = {
            'wsgi.url_scheme':'http',
            'HTTP_HOST':'example.com:80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url()
        self.assertEqual(result, 'http://example.com')

    def test_partial_application_url_with_http_host_default_port_https(self):
        environ = {
            'wsgi.url_scheme':'https',
            'HTTP_HOST':'example.com:443',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url()
        self.assertEqual(result, 'https://example.com')

    def test_partial_application_url_with_http_host_nondefault_port_http(self):
        environ = {
            'wsgi.url_scheme':'http',
            'HTTP_HOST':'example.com:8080',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url()
        self.assertEqual(result, 'http://example.com:8080')

    def test_partial_application_url_with_http_host_nondefault_port_https(self):
        environ = {
            'wsgi.url_scheme':'https',
            'HTTP_HOST':'example.com:4443',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url()
        self.assertEqual(result, 'https://example.com:4443')

    def test_partial_application_url_with_http_host_no_colon(self):
        environ = {
            'wsgi.url_scheme':'http',
            'HTTP_HOST':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url()
        self.assertEqual(result, 'http://example.com')

    def test_partial_application_url_no_http_host(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url()
        self.assertEqual(result, 'http://example.com')
        
    def test_partial_application_replace_port(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(port=8080)
        self.assertEqual(result, 'http://example.com:8080')

    def test_partial_application_replace_scheme_https_special_case(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(scheme='https')
        self.assertEqual(result, 'https://example.com')

    def test_partial_application_replace_scheme_https_special_case_avoid(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(scheme='https', port='8080')
        self.assertEqual(result, 'https://example.com:8080')

    def test_partial_application_replace_scheme_http_special_case(self):
        environ = {
            'wsgi.url_scheme':'https',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'8080',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(scheme='http')
        self.assertEqual(result, 'http://example.com')

    def test_partial_application_replace_scheme_http_special_case_avoid(self):
        environ = {
            'wsgi.url_scheme':'https',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'8000',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(scheme='http', port='8080')
        self.assertEqual(result, 'http://example.com:8080')
        
    def test_partial_application_replace_host_no_port(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(host='someotherhost.com')
        self.assertEqual(result, 'http://someotherhost.com')

    def test_partial_application_replace_host_with_port(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'8000',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(host='someotherhost.com:8080')
        self.assertEqual(result, 'http://someotherhost.com:8080')

    def test_partial_application_replace_host_and_port(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(host='someotherhost.com:8080',
                                                  port='8000')
        self.assertEqual(result, 'http://someotherhost.com:8000')

    def test_partial_application_replace_host_port_and_scheme(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'80',
            }
        request = self._makeOne(environ)
        result = request._partial_application_url(
            host='someotherhost.com:8080',
            port='8000',
            scheme='https',
            )
        self.assertEqual(result, 'https://someotherhost.com:8000')
        
    def test_partial_application_url_with_custom_script_name(self):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'example.com',
            'SERVER_PORT':'8000',
            }
        request = self._makeOne(environ)
        request.script_name = '/abc'
        result = request._partial_application_url()
        self.assertEqual(result, 'http://example.com:8000/abc') 
        
class Test_route_url(unittest.TestCase):
    def _callFUT(self, route_name, request, *elements, **kw):
        from pyramid.url import route_url
        return route_url(route_name, request, *elements, **kw)

    def _makeRequest(self):
        class Request(object):
            def route_url(self, route_name, *elements, **kw):
                self.route_name = route_name
                self.elements = elements
                self.kw = kw
                return 'route url'
        return Request()

    def test_it(self):
        request = self._makeRequest()
        result = self._callFUT('abc', request, 'a', _app_url='')
        self.assertEqual(result, 'route url')
        self.assertEqual(request.route_name, 'abc')
        self.assertEqual(request.elements, ('a',))
        self.assertEqual(request.kw, {'_app_url':''})

class Test_route_path(unittest.TestCase):
    def _callFUT(self, route_name, request, *elements, **kw):
        from pyramid.url import route_path
        return route_path(route_name, request, *elements, **kw)

    def _makeRequest(self):
        class Request(object):
            def route_path(self, route_name, *elements, **kw):
                self.route_name = route_name
                self.elements = elements
                self.kw = kw
                return 'route path'
        return Request()

    def test_it(self):
        request = self._makeRequest()
        result = self._callFUT('abc', request, 'a', _app_url='')
        self.assertEqual(result, 'route path')
        self.assertEqual(request.route_name, 'abc')
        self.assertEqual(request.elements, ('a',))
        self.assertEqual(request.kw, {'_app_url':''})

class Test_resource_url(unittest.TestCase):
    def _callFUT(self, resource, request, *elements, **kw):
        from pyramid.url import resource_url
        return resource_url(resource, request, *elements, **kw)

    def _makeRequest(self):
        class Request(object):
            def resource_url(self, resource, *elements, **kw):
                self.resource = resource
                self.elements = elements
                self.kw = kw
                return 'resource url'
        return Request()

    def test_it(self):
        request = self._makeRequest()
        result = self._callFUT('abc', request, 'a', _app_url='')
        self.assertEqual(result, 'resource url')
        self.assertEqual(request.resource, 'abc')
        self.assertEqual(request.elements, ('a',))
        self.assertEqual(request.kw, {'_app_url':''})

class Test_static_url(unittest.TestCase):
    def _callFUT(self, path, request, **kw):
        from pyramid.url import static_url
        return static_url(path, request, **kw)

    def _makeRequest(self):
        class Request(object):
            def static_url(self, path, **kw):
                self.path = path
                self.kw = kw
                return 'static url'
        return Request()

    def test_it_abs(self):
        request = self._makeRequest()
        result = self._callFUT('/foo/bar/abc', request, _app_url='')
        self.assertEqual(result, 'static url')
        self.assertEqual(request.path, '/foo/bar/abc')
        self.assertEqual(request.kw, {'_app_url':''})

    def test_it_absspec(self):
        request = self._makeRequest()
        result = self._callFUT('foo:abc', request, _anchor='anchor')
        self.assertEqual(result, 'static url')
        self.assertEqual(request.path, 'foo:abc')
        self.assertEqual(request.kw, {'_anchor':'anchor'})

    def test_it_rel(self):
        request = self._makeRequest()
        result = self._callFUT('abc', request, _app_url='')
        self.assertEqual(result, 'static url')
        self.assertEqual(request.path, 'pyramid.tests:abc')
        self.assertEqual(request.kw, {'_app_url':''})

class Test_static_path(unittest.TestCase):
    def _callFUT(self, path, request, **kw):
        from pyramid.url import static_path
        return static_path(path, request, **kw)

    def _makeRequest(self):
        class Request(object):
            def static_path(self, path, **kw):
                self.path = path
                self.kw = kw
                return 'static path'
        return Request()

    def test_it_abs(self):
        request = self._makeRequest()
        result = self._callFUT('/foo/bar/abc', request, _anchor='anchor')
        self.assertEqual(result, 'static path')
        self.assertEqual(request.path, '/foo/bar/abc')
        self.assertEqual(request.kw, {'_anchor':'anchor'})

    def test_it_absspec(self):
        request = self._makeRequest()
        result = self._callFUT('foo:abc', request, _anchor='anchor')
        self.assertEqual(result, 'static path')
        self.assertEqual(request.path, 'foo:abc')
        self.assertEqual(request.kw, {'_anchor':'anchor'})

    def test_it_rel(self):
        request = self._makeRequest()
        result = self._callFUT('abc', request, _app_url='')
        self.assertEqual(result, 'static path')
        self.assertEqual(request.path, 'pyramid.tests:abc')
        self.assertEqual(request.kw, {'_app_url':''})

class Test_current_route_url(unittest.TestCase):
    def _callFUT(self, request, *elements, **kw):
        from pyramid.url import current_route_url
        return current_route_url(request, *elements, **kw)

    def _makeRequest(self):
        class Request(object):
            def current_route_url(self, *elements, **kw):
                self.elements = elements
                self.kw = kw
                return 'current route url'
        return Request()

    def test_it(self):
        request = self._makeRequest()
        result = self._callFUT(request, 'abc', _app_url='')
        self.assertEqual(result, 'current route url')
        self.assertEqual(request.elements, ('abc',))
        self.assertEqual(request.kw, {'_app_url':''})

class Test_current_route_path(unittest.TestCase):
    def _callFUT(self, request, *elements, **kw):
        from pyramid.url import current_route_path
        return current_route_path(request, *elements, **kw)

    def _makeRequest(self):
        class Request(object):
            def current_route_path(self, *elements, **kw):
                self.elements = elements
                self.kw = kw
                return 'current route path'
        return Request()

    def test_it(self):
        request = self._makeRequest()
        result = self._callFUT(request, 'abc', _anchor='abc')
        self.assertEqual(result, 'current route path')
        self.assertEqual(request.elements, ('abc',))
        self.assertEqual(request.kw, {'_anchor':'abc'})

class Test_external_static_url_integration(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _makeRequest(self):
        from pyramid.request import Request
        return Request.blank('/')

    def test_generate_external_url(self):
        self.config.add_route('acme', 'https://acme.org/path/{foo}')
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertEqual(
            request.route_url('acme', foo='bar'),
            'https://acme.org/path/bar')

    def test_generate_external_url_without_scheme(self):
        self.config.add_route('acme', '//acme.org/path/{foo}')
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertEqual(
            request.route_url('acme', foo='bar'),
            'http://acme.org/path/bar')

    def test_generate_external_url_with_explicit_scheme(self):
        self.config.add_route('acme', '//acme.org/path/{foo}')
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertEqual(
            request.route_url('acme', foo='bar', _scheme='https'),
            'https://acme.org/path/bar')

    def test_generate_external_url_with_explicit_app_url(self):
        self.config.add_route('acme', 'http://acme.org/path/{foo}')
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertRaises(ValueError,
            request.route_url, 'acme', foo='bar', _app_url='http://fakeme.com')

    def test_generate_external_url_route_path(self):
        self.config.add_route('acme', 'https://acme.org/path/{foo}')
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertRaises(ValueError, request.route_path, 'acme', foo='bar')

    def test_generate_external_url_with_pregenerator(self):
        def pregenerator(request, elements, kw):
            kw['_query'] = {'q': 'foo'}
            return elements, kw
        self.config.add_route('acme', 'https://acme.org/path/{foo}',
                              pregenerator=pregenerator)
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertEqual(
            request.route_url('acme', foo='bar'),
            'https://acme.org/path/bar?q=foo')

    def test_external_url_with_route_prefix(self):
        def includeme(config):
            config.add_route('acme', '//acme.org/{foo}')
        self.config.include(includeme, route_prefix='some_prefix')
        request = self._makeRequest()
        request.registry = self.config.registry
        self.assertEqual(
            request.route_url('acme', foo='bar'),
            'http://acme.org/bar')

class DummyContext(object):
    def __init__(self, next=None):
        self.next = next
        
class DummyRoutesMapper:
    raise_exc = None
    def __init__(self, route=None, raise_exc=False):
        self.route = route

    def get_route(self, route_name):
        return self.route

class DummyRoute:
    pregenerator = None
    name = 'route'
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
    
def makeabs(*elements):
    if WIN: # pragma: no cover
        return r'c:\\' + os.path.sep.join(elements)
    else:
        return os.path.sep + os.path.sep.join(elements)
