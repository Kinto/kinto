import unittest

class TestDummyRootFactory(unittest.TestCase):
    def _makeOne(self, environ):
        from pyramid.testing import DummyRootFactory
        return DummyRootFactory(environ)

    def test_it(self):
        environ = {'bfg.routes.matchdict':{'a':1}}
        factory = self._makeOne(environ)
        self.assertEqual(factory.a, 1)

class TestDummySecurityPolicy(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.testing import DummySecurityPolicy
        return DummySecurityPolicy

    def _makeOne(self, userid=None, groupids=(), permissive=True):
        klass = self._getTargetClass()
        return klass(userid, groupids, permissive)

    def test_authenticated_userid(self):
        policy = self._makeOne('user')
        self.assertEqual(policy.authenticated_userid(None), 'user')

    def test_unauthenticated_userid(self):
        policy = self._makeOne('user')
        self.assertEqual(policy.unauthenticated_userid(None), 'user')

    def test_effective_principals_userid(self):
        policy = self._makeOne('user', ('group1',))
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        self.assertEqual(policy.effective_principals(None),
                         [Everyone, Authenticated, 'user', 'group1'])

    def test_effective_principals_nouserid(self):
        policy = self._makeOne()
        from pyramid.security import Everyone
        self.assertEqual(policy.effective_principals(None), [Everyone])

    def test_permits(self):
        policy = self._makeOne()
        self.assertEqual(policy.permits(None, None, None), True)
        
    def test_principals_allowed_by_permission(self):
        policy = self._makeOne('user', ('group1',))
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        result = policy.principals_allowed_by_permission(None, None)
        self.assertEqual(result, [Everyone, Authenticated, 'user', 'group1'])

    def test_forget(self):
        policy = self._makeOne()
        self.assertEqual(policy.forget(None), [])
        
    def test_remember(self):
        policy = self._makeOne()
        self.assertEqual(policy.remember(None, None), [])
        
        

class TestDummyResource(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.testing import DummyResource
        return DummyResource

    def _makeOne(self, name=None, parent=None, **kw):
        klass = self._getTargetClass()
        return klass(name, parent, **kw)

    def test__setitem__and__getitem__and__delitem__and__contains__and_get(self):
        class Dummy:
            pass
        dummy = Dummy()
        resource = self._makeOne()
        resource['abc'] = dummy
        self.assertEqual(dummy.__name__, 'abc')
        self.assertEqual(dummy.__parent__, resource)
        self.assertEqual(resource['abc'], dummy)
        self.assertEqual(resource.get('abc'), dummy)
        self.assertRaises(KeyError, resource.__getitem__, 'none')
        self.assertTrue('abc' in resource)
        del resource['abc']
        self.assertFalse('abc' in resource)
        self.assertEqual(resource.get('abc', 'foo'), 'foo')
        self.assertEqual(resource.get('abc'), None)

    def test_extra_params(self):
        resource = self._makeOne(foo=1)
        self.assertEqual(resource.foo, 1)
        
    def test_clone(self):
        resource = self._makeOne('name', 'parent', foo=1, bar=2)
        clone = resource.clone('name2', 'parent2', bar=1)
        self.assertEqual(clone.bar, 1)
        self.assertEqual(clone.__name__, 'name2')
        self.assertEqual(clone.__parent__, 'parent2')
        self.assertEqual(clone.foo, 1)

    def test_keys_items_values_len(self):
        class Dummy:
            pass
        resource = self._makeOne()
        resource['abc'] = Dummy()
        resource['def'] = Dummy()
        L = list
        self.assertEqual(L(resource.values()), L(resource.subs.values()))
        self.assertEqual(L(resource.items()), L(resource.subs.items()))
        self.assertEqual(L(resource.keys()), L(resource.subs.keys()))
        self.assertEqual(len(resource), 2)

    def test_nonzero(self):
        resource = self._makeOne()
        self.assertEqual(resource.__nonzero__(), True)

    def test_bool(self):
        resource = self._makeOne()
        self.assertEqual(resource.__bool__(), True)
        
    def test_ctor_with__provides__(self):
        resource = self._makeOne(__provides__=IDummy)
        self.assertTrue(IDummy.providedBy(resource))

class TestDummyRequest(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.testing import DummyRequest
        return DummyRequest

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def test_params(self):
        request = self._makeOne(params = {'say':'Hello'},
                                environ = {'PATH_INFO':'/foo'},
                                headers = {'X-Foo':'YUP'},
                               )
        self.assertEqual(request.params['say'], 'Hello')
        self.assertEqual(request.GET['say'], 'Hello')
        self.assertEqual(request.POST['say'], 'Hello')
        self.assertEqual(request.headers['X-Foo'], 'YUP')
        self.assertEqual(request.environ['PATH_INFO'], '/foo')

    def test_defaults(self):
        from pyramid.threadlocal import get_current_registry
        from pyramid.testing import DummySession
        request = self._makeOne()
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.application_url, 'http://example.com')
        self.assertEqual(request.host_url, 'http://example.com')
        self.assertEqual(request.path_url, 'http://example.com')
        self.assertEqual(request.url, 'http://example.com')
        self.assertEqual(request.host, 'example.com:80')
        self.assertEqual(request.content_length, 0)
        self.assertEqual(request.environ.get('PATH_INFO'), None)
        self.assertEqual(request.headers.get('X-Foo'), None)
        self.assertEqual(request.params.get('foo'), None)
        self.assertEqual(request.GET.get('foo'), None)
        self.assertEqual(request.POST.get('foo'), None)
        self.assertEqual(request.cookies.get('type'), None)
        self.assertEqual(request.path, '/')
        self.assertEqual(request.path_info, '/')
        self.assertEqual(request.script_name, '')
        self.assertEqual(request.path_qs, '')
        self.assertEqual(request.view_name, '')
        self.assertEqual(request.subpath, ())
        self.assertEqual(request.context, None)
        self.assertEqual(request.root, None)
        self.assertEqual(request.virtual_root, None)
        self.assertEqual(request.virtual_root_path, ())
        self.assertEqual(request.registry, get_current_registry())
        self.assertEqual(request.session.__class__, DummySession)

    def test_params_explicit(self):
        request = self._makeOne(params = {'foo':'bar'})
        self.assertEqual(request.params['foo'], 'bar')
        self.assertEqual(request.GET['foo'], 'bar')
        self.assertEqual(request.POST['foo'], 'bar')

    def test_environ_explicit(self):
        request = self._makeOne(environ = {'PATH_INFO':'/foo'})
        self.assertEqual(request.environ['PATH_INFO'], '/foo')

    def test_headers_explicit(self):
        request = self._makeOne(headers = {'X-Foo':'YUP'})
        self.assertEqual(request.headers['X-Foo'], 'YUP')

    def test_path_explicit(self):
        request = self._makeOne(path = '/abc')
        self.assertEqual(request.path, '/abc')

    def test_cookies_explicit(self):
        request = self._makeOne(cookies = {'type': 'gingersnap'})
        self.assertEqual(request.cookies['type'], 'gingersnap')

    def test_post_explicit(self):
        POST = {'foo': 'bar', 'baz': 'qux'}
        request = self._makeOne(post=POST)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.POST, POST)
        # N.B.:  Unlike a normal request, passing 'post' should *not* put
        #        explict POST data into params: doing so masks a possible
        #        XSS bug in the app.  Tests for apps which don't care about
        #        the distinction should just use 'params'.
        self.assertEqual(request.params, {})

    def test_post_empty_shadows_params(self):
        request = self._makeOne(params={'foo': 'bar'}, post={})
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.params.get('foo'), 'bar')
        self.assertEqual(request.POST.get('foo'), None)

    def test_kwargs(self):
        request = self._makeOne(water = 1)
        self.assertEqual(request.water, 1)

    def test_add_response_callback(self):
        request = self._makeOne()
        request.add_response_callback(1)
        self.assertEqual(list(request.response_callbacks), [1])

    def test_registry_is_config_registry_when_setup_is_called_after_ctor(self):
        # see https://github.com/Pylons/pyramid/issues/165
        from pyramid.registry import Registry
        from pyramid.config import Configurator
        request = self._makeOne()
        try:
            registry = Registry('this_test')
            config = Configurator(registry=registry)
            config.begin()
            self.assertTrue(request.registry is registry)
        finally:
            config.end()

    def test_set_registry(self):
        request = self._makeOne()
        request.registry = 'abc'
        self.assertEqual(request.registry, 'abc')

    def test_del_registry(self):
        # see https://github.com/Pylons/pyramid/issues/165
        from pyramid.registry import Registry
        from pyramid.config import Configurator
        request = self._makeOne()
        request.registry = 'abc'
        self.assertEqual(request.registry, 'abc')
        del request.registry
        try:
            registry = Registry('this_test')
            config = Configurator(registry=registry)
            config.begin()
            self.assertTrue(request.registry is registry)
        finally:
            config.end()

    def test_response_with_responsefactory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IResponseFactory
        registry = Registry('this_test')
        class ResponseFactory(object):
            pass
        registry.registerUtility(
            lambda r: ResponseFactory(), IResponseFactory
        )
        request = self._makeOne()
        request.registry = registry
        resp = request.response
        self.assertEqual(resp.__class__, ResponseFactory)
        self.assertTrue(request.response is resp) # reified

    def test_response_without_responsefactory(self):
        from pyramid.registry import Registry
        from pyramid.response import Response
        registry = Registry('this_test')
        request = self._makeOne()
        request.registry = registry
        resp = request.response
        self.assertEqual(resp.__class__, Response)
        self.assertTrue(request.response is resp) # reified
        

class TestDummyTemplateRenderer(unittest.TestCase):
    def _getTargetClass(self, ):
        from pyramid.testing import DummyTemplateRenderer
        return DummyTemplateRenderer

    def _makeOne(self, string_response=''):
        return self._getTargetClass()(string_response=string_response)

    def test_implementation(self):
        renderer = self._makeOne()
        impl = renderer.implementation()
        impl(a=1, b=2)
        self.assertEqual(renderer._implementation._received['a'], 1)
        self.assertEqual(renderer._implementation._received['b'], 2)

    def test_getattr(self):
        renderer = self._makeOne()
        renderer({'a':1})
        self.assertEqual(renderer.a, 1)
        self.assertRaises(AttributeError, renderer.__getattr__, 'b')

    def test_assert_(self):
        renderer = self._makeOne()
        renderer({'a':1, 'b':2})
        self.assertRaises(AssertionError, renderer.assert_, c=1)
        self.assertRaises(AssertionError, renderer.assert_, b=3)
        self.assertTrue(renderer.assert_(a=1, b=2))
        
    def test_nondefault_string_response(self):
        renderer = self._makeOne('abc')
        result = renderer({'a':1, 'b':2})
        self.assertEqual(result, 'abc')

class Test_setUp(unittest.TestCase):
    def _callFUT(self, **kw):
        from pyramid.testing import setUp
        return setUp(**kw)

    def tearDown(self):
        from pyramid.threadlocal import manager
        manager.clear()
        getSiteManager = self._getSM()
        if getSiteManager is not None:
            getSiteManager.reset()

    def _getSM(self):
        try:
            from zope.component import getSiteManager
        except ImportError: # pragma: no cover
            getSiteManager = None
        return getSiteManager

    def _assertSMHook(self, hook):
        getSiteManager = self._getSM()
        if getSiteManager is not None:
            result = getSiteManager.sethook(None)
            self.assertEqual(result, hook)

    def test_it_defaults(self):
        from pyramid.threadlocal import manager
        from pyramid.threadlocal import get_current_registry
        from pyramid.registry import Registry
        old = True
        manager.push(old)
        config = self._callFUT()
        current = manager.get()
        self.assertFalse(current is old)
        self.assertEqual(config.registry, current['registry'])
        self.assertEqual(current['registry'].__class__, Registry)
        self.assertEqual(current['request'], None)
        self.assertEqual(config.package.__name__, 'pyramid.tests')
        self._assertSMHook(get_current_registry)

    def test_it_with_registry(self):
        from pyramid.registry import Registry
        from pyramid.threadlocal import manager
        registry = Registry()
        self._callFUT(registry=registry)
        current = manager.get()
        self.assertEqual(current['registry'], registry)
            
    def test_it_with_request(self):
        from pyramid.threadlocal import manager
        request = object()
        self._callFUT(request=request)
        current = manager.get()
        self.assertEqual(current['request'], request)

    def test_it_with_package(self):
        config = self._callFUT(package='pyramid')
        self.assertEqual(config.package.__name__, 'pyramid')

    def test_it_with_hook_zca_false(self):
        from pyramid.registry import Registry
        registry = Registry()
        self._callFUT(registry=registry, hook_zca=False)
        getSiteManager = self._getSM()
        if getSiteManager is not None:
            sm = getSiteManager()
            self.assertFalse(sm is registry)

    def test_it_with_settings_passed_explicit_registry(self):
        from pyramid.registry import Registry
        registry = Registry()
        self._callFUT(registry=registry, hook_zca=False, settings=dict(a=1))
        self.assertEqual(registry.settings['a'], 1)
        
    def test_it_with_settings_passed_implicit_registry(self):
        config = self._callFUT(hook_zca=False, settings=dict(a=1))
        self.assertEqual(config.registry.settings['a'], 1)

class Test_cleanUp(Test_setUp):
    def _callFUT(self, *arg, **kw):
        from pyramid.testing import cleanUp
        return cleanUp(*arg, **kw)
        
class Test_tearDown(unittest.TestCase):
    def _callFUT(self, **kw):
        from pyramid.testing import tearDown
        return tearDown(**kw)

    def tearDown(self):
        from pyramid.threadlocal import manager
        manager.clear()
        getSiteManager = self._getSM()
        if getSiteManager is not None:
            getSiteManager.reset()

    def _getSM(self):
        try:
            from zope.component import getSiteManager
        except ImportError: # pragma: no cover
            getSiteManager = None
        return getSiteManager

    def _assertSMHook(self, hook):
        getSiteManager = self._getSM()
        if getSiteManager is not None:
            result = getSiteManager.sethook(None)
            self.assertEqual(result, hook)

    def _setSMHook(self, hook):
        getSiteManager = self._getSM()
        if getSiteManager is not None:
            getSiteManager.sethook(hook)

    def test_defaults(self):
        from pyramid.threadlocal import manager
        registry = DummyRegistry()
        old = {'registry':registry}
        hook = lambda *arg: None
        try:
            self._setSMHook(hook)
            manager.push(old)
            self._callFUT()
            current = manager.get()
            self.assertNotEqual(current, old)
            self.assertEqual(registry.inited, 2)
        finally:
            getSiteManager = self._getSM()
            if getSiteManager is not None:
                result = getSiteManager.sethook(None)
                self.assertNotEqual(result, hook)

    def test_registry_cannot_be_inited(self):
        from pyramid.threadlocal import manager
        registry = DummyRegistry()
        def raiseit(name):
            raise TypeError
        registry.__init__ = raiseit
        old = {'registry':registry}
        try:
            manager.push(old)
            self._callFUT() # doesn't blow up
            current = manager.get()
            self.assertNotEqual(current, old)
            self.assertEqual(registry.inited, 1)
        finally:
            manager.clear()

    def test_unhook_zc_false(self):
        hook = lambda *arg: None
        try:
            self._setSMHook(hook)
            self._callFUT(unhook_zca=False)
        finally:
            self._assertSMHook(hook)

class TestDummyRendererFactory(unittest.TestCase):
    def _makeOne(self, name, factory):
        from pyramid.testing import DummyRendererFactory
        return DummyRendererFactory(name, factory)

    def test_add_no_colon(self):
        f = self._makeOne('name', None)
        f.add('spec', 'renderer')
        self.assertEqual(f.renderers['spec'], 'renderer')

    def test_add_with_colon(self):
        f = self._makeOne('name', None)
        f.add('spec:spec2', 'renderer')
        self.assertEqual(f.renderers['spec:spec2'], 'renderer')
        self.assertEqual(f.renderers['spec2'], 'renderer')

    def test_call(self):
        f = self._makeOne('name', None)
        f.renderers['spec'] = 'renderer'
        info = DummyRendererInfo({'name':'spec'})
        self.assertEqual(f(info), 'renderer')
        
    def test_call2(self):
        f = self._makeOne('name', None)
        f.renderers['spec'] = 'renderer'
        info = DummyRendererInfo({'name':'spec:spec'})
        self.assertEqual(f(info), 'renderer')

    def test_call3(self):
        def factory(spec):
            return 'renderer'
        f = self._makeOne('name', factory)
        info = DummyRendererInfo({'name':'spec'})
        self.assertEqual(f(info), 'renderer')

    def test_call_miss(self):
        f = self._makeOne('name', None)
        info = DummyRendererInfo({'name':'spec'})
        self.assertRaises(KeyError, f, info)

class TestMockTemplate(unittest.TestCase):
    def _makeOne(self, response):
        from pyramid.testing import MockTemplate
        return MockTemplate(response)

    def test_getattr(self):
        template = self._makeOne(None)
        self.assertEqual(template.foo, template)

    def test_getitem(self):
        template = self._makeOne(None)
        self.assertEqual(template['foo'], template)

    def test_call(self):
        template = self._makeOne('123')
        self.assertEqual(template(), '123')

class Test_skip_on(unittest.TestCase):
    def setUp(self):
        from pyramid.testing import skip_on
        self.os_name = skip_on.os_name
        skip_on.os_name = 'wrong'

    def tearDown(self):
        from pyramid.testing import skip_on
        skip_on.os_name = self.os_name
        
    def _callFUT(self, *platforms):
        from pyramid.testing import skip_on
        return skip_on(*platforms)

    def test_wrong_platform(self):
        def foo(): return True
        decorated = self._callFUT('wrong')(foo)
        self.assertEqual(decorated(), None)
        
    def test_ok_platform(self):
        def foo(): return True
        decorated = self._callFUT('ok')(foo)
        self.assertEqual(decorated(), True)

class TestDummySession(unittest.TestCase):
    def _makeOne(self):
        from pyramid.testing import DummySession
        return DummySession()

    def test_instance_conforms(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import ISession
        session = self._makeOne()
        verifyObject(ISession, session)

    def test_changed(self):
        session = self._makeOne()
        self.assertEqual(session.changed(), None)

    def test_invalidate(self):
        session = self._makeOne()
        session['a'] = 1
        self.assertEqual(session.invalidate(), None)
        self.assertFalse('a' in session)

    def test_flash_default(self):
        session = self._makeOne()
        session.flash('msg1')
        session.flash('msg2')
        self.assertEqual(session['_f_'], ['msg1', 'msg2'])
        
    def test_flash_mixed(self):
        session = self._makeOne()
        session.flash('warn1', 'warn')
        session.flash('warn2', 'warn')
        session.flash('err1', 'error')
        session.flash('err2', 'error')
        self.assertEqual(session['_f_warn'], ['warn1', 'warn2'])

    def test_pop_flash_default_queue(self):
        session = self._makeOne()
        queue = ['one', 'two']
        session['_f_'] = queue
        result = session.pop_flash()
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_'), None)

    def test_pop_flash_nodefault_queue(self):
        session = self._makeOne()
        queue = ['one', 'two']
        session['_f_error'] = queue
        result = session.pop_flash('error')
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_error'), None)

    def test_peek_flash_default_queue(self):
        session = self._makeOne()
        queue = ['one', 'two']
        session['_f_'] = queue
        result = session.peek_flash()
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_'), queue)

    def test_peek_flash_nodefault_queue(self):
        session = self._makeOne()
        queue = ['one', 'two']
        session['_f_error'] = queue
        result = session.peek_flash('error')
        self.assertEqual(result, queue)
        self.assertEqual(session.get('_f_error'), queue)

    def test_new_csrf_token(self):
        session = self._makeOne()
        token = session.new_csrf_token()
        self.assertEqual(token, session['_csrft_'])

    def test_get_csrf_token(self):
        session = self._makeOne()
        session['_csrft_'] = 'token'
        token = session.get_csrf_token()
        self.assertEqual(token, 'token')
        self.assertTrue('_csrft_' in session)

    def test_get_csrf_token_generates_token(self):
        session = self._makeOne()
        token = session.get_csrf_token()
        self.assertNotEqual(token, None)
        self.assertTrue(len(token) >= 1)

from zope.interface import Interface
from zope.interface import implementer
        
class IDummy(Interface):
    pass

@implementer(IDummy)
class DummyEvent:
    pass
    
class DummyFactory:
    def __init__(self, environ):
        """ """

class DummyRegistry(object):
    inited = 0
    __name__ = 'name'
    def __init__(self, name=''):
        self.inited = self.inited + 1
        
class DummyRendererInfo(object):
    def __init__(self, kw):
        self.__dict__.update(kw)
        
class Test_testConfig(unittest.TestCase):

    def _setUp(self, **kw):
        self._log.append(('setUp', kw))
        return 'fake config'

    def _tearDown(self, **kw):
        self._log.append(('tearDown', kw))

    def setUp(self):
        from pyramid import testing
        self._log = []
        self._orig_setUp = testing.setUp
        testing.setUp = self._setUp
        self._orig_tearDown = testing.tearDown
        testing.tearDown = self._tearDown

    def tearDown(self):
        from pyramid import testing
        testing.setUp = self._orig_setUp
        testing.tearDown = self._orig_tearDown

    def _callFUT(self, inner, **kw):
        from pyramid.testing import testConfig
        with testConfig(**kw) as config:
            inner(config)

    def test_ok_calls(self):
        self.assertEqual(self._log, [])
        def inner(config):
            self.assertEqual(self._log,
                    [('setUp',
                        {'autocommit': True,
                            'hook_zca': True,
                            'registry': None,
                            'request': None,
                            'settings': None})])
            self._log.pop()
        self._callFUT(inner)
        self.assertEqual(self._log,
                [('tearDown', {'unhook_zca': True})])

    def test_teardown_called_on_exception(self):
        class TestException(Exception):
            pass
        def inner(config):
            self._log = []
            raise TestException('oops')
        self.assertRaises(TestException, self._callFUT, inner)
        self.assertEqual(self._log[0][0], 'tearDown')

    def test_ok_get_config(self):
        def inner(config):
            self.assertEqual(config, 'fake config')
        self._callFUT(inner)
