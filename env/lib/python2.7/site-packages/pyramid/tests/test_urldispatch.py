import unittest
from pyramid import testing
from pyramid.compat import (
    text_,
    PY2,
    )

class TestRoute(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.urldispatch import Route
        return Route

    def _makeOne(self, *arg):
        return self._getTargetClass()(*arg)

    def test_provides_IRoute(self):
        from pyramid.interfaces import IRoute
        from zope.interface.verify import verifyObject
        verifyObject(IRoute, self._makeOne('name', 'pattern'))

    def test_ctor(self):
        import types
        route = self._makeOne('name', ':path', 'factory')
        self.assertEqual(route.pattern, ':path')
        self.assertEqual(route.path, ':path')
        self.assertEqual(route.name, 'name')
        self.assertEqual(route.factory, 'factory')
        self.assertTrue(route.generate.__class__ is types.FunctionType)
        self.assertTrue(route.match.__class__ is types.FunctionType)

    def test_ctor_defaults(self):
        import types
        route = self._makeOne('name', ':path')
        self.assertEqual(route.pattern, ':path')
        self.assertEqual(route.path, ':path')
        self.assertEqual(route.name, 'name')
        self.assertEqual(route.factory, None)
        self.assertTrue(route.generate.__class__ is types.FunctionType)
        self.assertTrue(route.match.__class__ is types.FunctionType)

    def test_match(self):
        route = self._makeOne('name', ':path')
        self.assertEqual(route.match('/whatever'), {'path':'whatever'})

    def test_generate(self):
        route = self._makeOne('name', ':path')
        self.assertEqual(route.generate({'path':'abc'}), '/abc')

class RoutesMapperTests(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def _getRequest(self, **kw):
        from pyramid.threadlocal import get_current_registry
        environ = {'SERVER_NAME':'localhost',
                   'wsgi.url_scheme':'http'}
        environ.update(kw)
        request = DummyRequest(environ)
        reg = get_current_registry()
        request.registry = reg
        return request

    def _getTargetClass(self):
        from pyramid.urldispatch import RoutesMapper
        return RoutesMapper

    def _makeOne(self):
        klass = self._getTargetClass()
        return klass()

    def test_provides_IRoutesMapper(self):
        from pyramid.interfaces import IRoutesMapper
        from zope.interface.verify import verifyObject
        verifyObject(IRoutesMapper, self._makeOne())

    def test_no_route_matches(self):
        mapper = self._makeOne()
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['match'], None)
        self.assertEqual(result['route'], None)

    def test_connect_name_exists_removes_old(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article')
        mapper.connect('foo', 'archives/:action/:article2')
        self.assertEqual(len(mapper.routelist), 1)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article2')
        self.assertEqual(mapper.routelist[0].pattern,
                         'archives/:action/:article2')

    def test_connect_static(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article', static=True)
        self.assertEqual(len(mapper.routelist), 0)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article')

    def test_connect_static_overridden(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article', static=True)
        self.assertEqual(len(mapper.routelist), 0)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article')
        mapper.connect('foo', 'archives/:action/:article2')
        self.assertEqual(len(mapper.routelist), 1)
        self.assertEqual(len(mapper.routes), 1)
        self.assertEqual(mapper.routes['foo'].pattern,
                         'archives/:action/:article2')
        self.assertEqual(mapper.routelist[0].pattern,
                         'archives/:action/:article2')

    def test___call__pathinfo_cant_be_decoded(self):
        from pyramid.exceptions import URLDecodeError
        mapper = self._makeOne()
        if PY2:
            path_info = b'\xff\xfe\xe6\x00'
        else:
            path_info = b'\xff\xfe\xe6\x00'.decode('latin-1')
        request = self._getRequest(PATH_INFO=path_info)
        self.assertRaises(URLDecodeError, mapper, request)

    def test___call__route_matches(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article')
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['foo'])
        self.assertEqual(result['match']['action'], 'action1')
        self.assertEqual(result['match']['article'], 'article1')

    def test___call__route_matches_with_predicates(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/:article',
                       predicates=[lambda *arg: True])
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['foo'])
        self.assertEqual(result['match']['action'], 'action1')
        self.assertEqual(result['match']['article'], 'article1')

    def test___call__route_fails_to_match_with_predicates(self):
        mapper = self._makeOne()
        mapper.connect('foo', 'archives/:action/article1',
                       predicates=[lambda *arg: True, lambda *arg: False])
        mapper.connect('bar', 'archives/:action/:article')
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['bar'])
        self.assertEqual(result['match']['action'], 'action1')
        self.assertEqual(result['match']['article'], 'article1')

    def test___call__custom_predicate_gets_info(self):
        mapper = self._makeOne()
        def pred(info, request):
            self.assertEqual(info['match'], {'action':'action1'})
            self.assertEqual(info['route'], mapper.routes['foo'])
            return True
        mapper.connect('foo', 'archives/:action/article1', predicates=[pred])
        request = self._getRequest(PATH_INFO='/archives/action1/article1')
        mapper(request)

    def test_cc_bug(self):
        # "unordered" as reported in IRC by author of
        # http://labs.creativecommons.org/2010/01/13/cc-engine-and-web-non-frameworks/
        mapper = self._makeOne()
        mapper.connect('rdf', 'licenses/:license_code/:license_version/rdf')
        mapper.connect('juri',
                       'licenses/:license_code/:license_version/:jurisdiction')

        request = self._getRequest(PATH_INFO='/licenses/1/v2/rdf')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['rdf'])
        self.assertEqual(result['match']['license_code'], '1')
        self.assertEqual(result['match']['license_version'], 'v2')

        request = self._getRequest(PATH_INFO='/licenses/1/v2/usa')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['juri'])
        self.assertEqual(result['match']['license_code'], '1')
        self.assertEqual(result['match']['license_version'], 'v2')
        self.assertEqual(result['match']['jurisdiction'], 'usa')

    def test___call__root_route_matches(self):
        mapper = self._makeOne()
        mapper.connect('root', '')
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__root_route_matches2(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__root_route_when_path_info_empty(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest(PATH_INFO='')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__root_route_when_path_info_notempty(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest(PATH_INFO='/')
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test___call__no_path_info(self):
        mapper = self._makeOne()
        mapper.connect('root', '/')
        request = self._getRequest()
        result = mapper(request)
        self.assertEqual(result['route'], mapper.routes['root'])
        self.assertEqual(result['match'], {})

    def test_has_routes(self):
        mapper = self._makeOne()
        self.assertEqual(mapper.has_routes(), False)
        mapper.connect('whatever', 'archives/:action/:article')
        self.assertEqual(mapper.has_routes(), True)

    def test_get_routes(self):
        from pyramid.urldispatch import Route
        mapper = self._makeOne()
        self.assertEqual(mapper.get_routes(), [])
        mapper.connect('whatever', 'archives/:action/:article')
        routes = mapper.get_routes()
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].__class__, Route)

    def test_get_route_matches(self):
        mapper = self._makeOne()
        mapper.connect('whatever', 'archives/:action/:article')
        result = mapper.get_route('whatever')
        self.assertEqual(result.pattern, 'archives/:action/:article')

    def test_get_route_misses(self):
        mapper = self._makeOne()
        result = mapper.get_route('whatever')
        self.assertEqual(result, None)

    def test_generate(self):
        mapper = self._makeOne()
        def generator(kw):
            return 123
        route = DummyRoute(generator)
        mapper.routes['abc'] =  route
        self.assertEqual(mapper.generate('abc', {}), 123)

class TestCompileRoute(unittest.TestCase):
    def _callFUT(self, pattern):
        from pyramid.urldispatch import _compile_route
        return _compile_route(pattern)

    def test_no_star(self):
        matcher, generator = self._callFUT('/foo/:baz/biz/:buz/bar')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2}), '/foo/1/biz/2/bar')

    def test_with_star(self):
        matcher, generator = self._callFUT('/foo/:baz/biz/:buz/bar*traverse')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz', 'traverse':()})
        self.assertEqual(matcher('/foo/baz/biz/buz/bar/everything/else/here'),
                         {'baz':'baz', 'buz':'buz',
                          'traverse':('everything', 'else', 'here')})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator(
            {'baz':1, 'buz':2, 'traverse':'/a/b'}), '/foo/1/biz/2/bar/a/b')
    
    def test_with_bracket_star(self):
        matcher, generator = self._callFUT(
            '/foo/{baz}/biz/{buz}/bar{remainder:.*}')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz', 'remainder':''})
        self.assertEqual(matcher('/foo/baz/biz/buz/bar/everything/else/here'),
                         {'baz':'baz', 'buz':'buz',
                          'remainder':'/everything/else/here'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator(
            {'baz':1, 'buz':2, 'remainder':'/a/b'}), '/foo/1/biz/2/bar/a/b')

    def test_no_beginning_slash(self):
        matcher, generator = self._callFUT('foo/:baz/biz/:buz/bar')
        self.assertEqual(matcher('/foo/baz/biz/buz/bar'),
                         {'baz':'baz', 'buz':'buz'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2}), '/foo/1/biz/2/bar')

    def test_custom_regex(self):
        matcher, generator = self._callFUT('foo/{baz}/biz/{buz:[^/\.]+}.{bar}')
        self.assertEqual(matcher('/foo/baz/biz/buz.bar'),
                         {'baz':'baz', 'buz':'buz', 'bar':'bar'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2, 'bar': 'html'}),
                         '/foo/1/biz/2.html')
    
    def test_custom_regex_with_colons(self):
        matcher, generator = self._callFUT('foo/{baz}/biz/{buz:(?:[^/\.]+)}.{bar}')
        self.assertEqual(matcher('/foo/baz/biz/buz.bar'),
                         {'baz':'baz', 'buz':'buz', 'bar':'bar'})
        self.assertEqual(matcher('foo/baz/biz/buz/bar'), None)
        self.assertEqual(generator({'baz':1, 'buz':2, 'bar': 'html'}),
                         '/foo/1/biz/2.html')

    def test_mixed_newstyle_oldstyle_pattern_defaults_to_newstyle(self):
        # pattern: '\\/foo\\/(?P<baz>abc)\\/biz\\/(?P<buz>[^/]+)\\/bar$'
        # note presence of :abc in pattern (oldstyle match)
        matcher, generator = self._callFUT('foo/{baz:abc}/biz/{buz}/bar')
        self.assertEqual(matcher('/foo/abc/biz/buz/bar'),
                         {'baz':'abc', 'buz':'buz'})
        self.assertEqual(generator({'baz':1, 'buz':2}), '/foo/1/biz/2/bar')

    def test_custom_regex_with_embedded_squigglies(self):
        matcher, generator = self._callFUT('/{buz:\d{4}}')
        self.assertEqual(matcher('/2001'), {'buz':'2001'})
        self.assertEqual(matcher('/200'), None)
        self.assertEqual(generator({'buz':2001}), '/2001')

    def test_custom_regex_with_embedded_squigglies2(self):
        matcher, generator = self._callFUT('/{buz:\d{3,4}}')
        self.assertEqual(matcher('/2001'), {'buz':'2001'})
        self.assertEqual(matcher('/200'), {'buz':'200'})
        self.assertEqual(matcher('/20'), None)
        self.assertEqual(generator({'buz':2001}), '/2001')

    def test_custom_regex_with_embedded_squigglies3(self):
        matcher, generator = self._callFUT(
            '/{buz:(\d{2}|\d{4})-[a-zA-Z]{3,4}-\d{2}}')
        self.assertEqual(matcher('/2001-Nov-15'), {'buz':'2001-Nov-15'})
        self.assertEqual(matcher('/99-June-10'), {'buz':'99-June-10'})
        self.assertEqual(matcher('/2-Nov-15'), None)
        self.assertEqual(matcher('/200-Nov-15'), None)
        self.assertEqual(matcher('/2001-No-15'), None)
        self.assertEqual(generator({'buz':'2001-Nov-15'}), '/2001-Nov-15')
        self.assertEqual(generator({'buz':'99-June-10'}), '/99-June-10')

    def test_pattern_with_high_order_literal(self):
        pattern = text_(b'/La Pe\xc3\xb1a/{x}', 'utf-8')
        matcher, generator = self._callFUT(pattern)
        self.assertEqual(matcher(text_(b'/La Pe\xc3\xb1a/x', 'utf-8')),
                         {'x':'x'})
        self.assertEqual(generator({'x':'1'}), '/La%20Pe%C3%B1a/1')

    def test_pattern_generate_with_high_order_dynamic(self):
        pattern = '/{x}'
        _, generator = self._callFUT(pattern)
        self.assertEqual(
            generator({'x':text_(b'La Pe\xc3\xb1a', 'utf-8')}),
            '/La%20Pe%C3%B1a')

    def test_docs_sample_generate(self):
        # sample from urldispatch.rst
        pattern = text_(b'/La Pe\xc3\xb1a/{city}', 'utf-8')
        _, generator = self._callFUT(pattern)
        self.assertEqual(
            generator({'city':text_(b'Qu\xc3\xa9bec', 'utf-8')}),
            '/La%20Pe%C3%B1a/Qu%C3%A9bec')

    def test_generate_with_mixedtype_values(self):
        pattern = '/{city}/{state}'
        _, generator = self._callFUT(pattern)
        result = generator(
            {'city': text_(b'Qu\xc3\xa9bec', 'utf-8'),
             'state': b'La Pe\xc3\xb1a'}
            )
        self.assertEqual(result, '/Qu%C3%A9bec/La%20Pe%C3%B1a')
        # should be a native string
        self.assertEqual(type(result), str)

    def test_highorder_pattern_utf8(self):
        pattern = b'/La Pe\xc3\xb1a/{city}'
        self.assertRaises(ValueError, self._callFUT, pattern)

    def test_generate_with_string_remainder_and_unicode_replacement(self):
        pattern = text_(b'/abc*remainder', 'utf-8')
        _, generator = self._callFUT(pattern)
        result = generator(
            {'remainder': text_(b'/Qu\xc3\xa9bec/La Pe\xc3\xb1a', 'utf-8')}
            )
        self.assertEqual(result, '/abc/Qu%C3%A9bec/La%20Pe%C3%B1a')
        # should be a native string
        self.assertEqual(type(result), str)

    def test_generate_with_string_remainder_and_nonstring_replacement(self):
        pattern = text_(b'/abc/*remainder', 'utf-8')
        _, generator = self._callFUT(pattern)
        result = generator(
            {'remainder': None}
            )
        self.assertEqual(result, '/abc/None')
        # should be a native string
        self.assertEqual(type(result), str)

class TestCompileRouteFunctional(unittest.TestCase):
    def matches(self, pattern, path, expected):
        from pyramid.urldispatch import _compile_route
        matcher = _compile_route(pattern)[0]
        result = matcher(path)
        self.assertEqual(result, expected)

    def generates(self, pattern, dict, result):
        from pyramid.urldispatch import _compile_route
        self.assertEqual(_compile_route(pattern)[1](dict), result)

    def test_matcher_functional_notdynamic(self):
        self.matches('/', '', None)
        self.matches('', '', None)
        self.matches('/', '/foo', None)
        self.matches('/foo/', '/foo', None)
        self.matches('', '/', {})
        self.matches('/', '/', {})

    def test_matcher_functional_newstyle(self):
        self.matches('/{x}', '', None)
        self.matches('/{x}', '/', None)
        self.matches('/abc/{def}', '/abc/', None)
        self.matches('/{x}', '/a', {'x':'a'})
        self.matches('zzz/{x}', '/zzz/abc', {'x':'abc'})
        self.matches('zzz/{x}*traverse', '/zzz/abc', {'x':'abc', 'traverse':()})
        self.matches('zzz/{x}*traverse', '/zzz/abc/def/g',
                     {'x':'abc', 'traverse':('def', 'g')})
        self.matches('*traverse', '/zzz/abc', {'traverse':('zzz', 'abc')})
        self.matches('*traverse', '/zzz/ abc', {'traverse':('zzz', ' abc')})
        #'/La%20Pe%C3%B1a'
        self.matches('{x}', text_(b'/La Pe\xc3\xb1a', 'utf-8'),
                     {'x':text_(b'La Pe\xc3\xb1a', 'utf-8')})
        # '/La%20Pe%C3%B1a/x'
        self.matches('*traverse', text_(b'/La Pe\xc3\xb1a/x'),
                     {'traverse':(text_(b'La Pe\xc3\xb1a'), 'x')})
        self.matches('/foo/{id}.html', '/foo/bar.html', {'id':'bar'})
        self.matches('/{num:[0-9]+}/*traverse', '/555/abc/def',
                     {'num':'555', 'traverse':('abc', 'def')})
        self.matches('/{num:[0-9]*}/*traverse', '/555/abc/def',
                     {'num':'555', 'traverse':('abc', 'def')})
        self.matches('zzz/{_}', '/zzz/abc', {'_':'abc'})
        self.matches('zzz/{_abc}', '/zzz/abc', {'_abc':'abc'})
        self.matches('zzz/{abc_def}', '/zzz/abc', {'abc_def':'abc'})

    def test_matcher_functional_oldstyle(self):
        self.matches('/:x', '', None)
        self.matches('/:x', '/', None)
        self.matches('/abc/:def', '/abc/', None)
        self.matches('/:x', '/a', {'x':'a'})
        self.matches('zzz/:x', '/zzz/abc', {'x':'abc'})
        self.matches('zzz/:x*traverse', '/zzz/abc', {'x':'abc', 'traverse':()})
        self.matches('zzz/:x*traverse', '/zzz/abc/def/g',
                     {'x':'abc', 'traverse':('def', 'g')})
        self.matches('*traverse', '/zzz/abc', {'traverse':('zzz', 'abc')})
        self.matches('*traverse', '/zzz/ abc', {'traverse':('zzz', ' abc')})
        #'/La%20Pe%C3%B1a'
        # pattern, path, expected
        self.matches(':x', text_(b'/La Pe\xc3\xb1a', 'utf-8'),
                     {'x':text_(b'La Pe\xc3\xb1a', 'utf-8')})
        # '/La%20Pe%C3%B1a/x'
        self.matches('*traverse', text_(b'/La Pe\xc3\xb1a/x', 'utf-8'),
                     {'traverse':(text_(b'La Pe\xc3\xb1a', 'utf-8'), 'x')})
        self.matches('/foo/:id.html', '/foo/bar.html', {'id':'bar'})
        self.matches('/foo/:id_html', '/foo/bar_html', {'id_html':'bar_html'})
        self.matches('zzz/:_', '/zzz/abc', {'_':'abc'})
        self.matches('zzz/:_abc', '/zzz/abc', {'_abc':'abc'})
        self.matches('zzz/:abc_def', '/zzz/abc', {'abc_def':'abc'})

    def test_generator_functional_notdynamic(self):
        self.generates('', {}, '/')
        self.generates('/', {}, '/')

    def test_generator_functional_newstyle(self):
        self.generates('/{x}', {'x':''}, '/')
        self.generates('/{x}', {'x':'a'}, '/a')
        self.generates('zzz/{x}', {'x':'abc'}, '/zzz/abc')
        self.generates('zzz/{x}*traverse', {'x':'abc', 'traverse':''},
                       '/zzz/abc')
        self.generates('zzz/{x}*traverse', {'x':'abc', 'traverse':'/def/g'},
                       '/zzz/abc/def/g')
        self.generates('/{x}', {'x':text_(b'/La Pe\xc3\xb1a', 'utf-8')},
                       '//La%20Pe%C3%B1a')
        self.generates('/{x}*y', {'x':text_(b'/La Pe\xc3\xb1a', 'utf-8'),
                                 'y':'/rest/of/path'},
                       '//La%20Pe%C3%B1a/rest/of/path')
        self.generates('*traverse', {'traverse':('a', text_(b'La Pe\xf1a'))},
                       '/a/La%20Pe%C3%B1a')
        self.generates('/foo/{id}.html', {'id':'bar'}, '/foo/bar.html')
        self.generates('/foo/{_}', {'_':'20'}, '/foo/20')
        self.generates('/foo/{_abc}', {'_abc':'20'}, '/foo/20')
        self.generates('/foo/{abc_def}', {'abc_def':'20'}, '/foo/20')
        
    def test_generator_functional_oldstyle(self):
        self.generates('/:x', {'x':''}, '/')
        self.generates('/:x', {'x':'a'}, '/a')
        self.generates('zzz/:x', {'x':'abc'}, '/zzz/abc')
        self.generates('zzz/:x*traverse', {'x':'abc', 'traverse':''},
                       '/zzz/abc')
        self.generates('zzz/:x*traverse', {'x':'abc', 'traverse':'/def/g'},
                       '/zzz/abc/def/g')
        self.generates('/:x', {'x':text_(b'/La Pe\xc3\xb1a', 'utf-8')},
                       '//La%20Pe%C3%B1a')
        self.generates('/:x*y', {'x':text_(b'/La Pe\xc3\xb1a', 'utf-8'),
                                 'y':'/rest/of/path'},
                       '//La%20Pe%C3%B1a/rest/of/path')
        self.generates('*traverse', {'traverse':('a', text_(b'La Pe\xf1a'))},
                       '/a/La%20Pe%C3%B1a')
        self.generates('/foo/:id.html', {'id':'bar'}, '/foo/bar.html')
        self.generates('/foo/:_', {'_':'20'}, '/foo/20')
        self.generates('/foo/:_abc', {'_abc':'20'}, '/foo/20')
        self.generates('/foo/:abc_def', {'abc_def':'20'}, '/foo/20')

class DummyContext(object):
    """ """
        
class DummyRequest(object):
    def __init__(self, environ):
        self.environ = environ
    
class DummyRoute(object):
    def __init__(self, generator):
        self.generate = generator
        
