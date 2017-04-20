import unittest

from pyramid.compat import text_
from pyramid.security import AuthenticationAPIMixin, AuthorizationAPIMixin
from pyramid.tests.test_config import IDummy

class TestingConfiguratorMixinTests(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_testing_securitypolicy(self):
        from pyramid.testing import DummySecurityPolicy
        config = self._makeOne(autocommit=True)
        config.testing_securitypolicy('user', ('group1', 'group2'),
                                      permissive=False)
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        ut = config.registry.getUtility(IAuthenticationPolicy)
        self.assertTrue(isinstance(ut, DummySecurityPolicy))
        ut = config.registry.getUtility(IAuthorizationPolicy)
        self.assertEqual(ut.userid, 'user')
        self.assertEqual(ut.groupids, ('group1', 'group2'))
        self.assertEqual(ut.permissive, False)

    def test_testing_securitypolicy_remember_result(self):
        from pyramid.security import remember
        config = self._makeOne(autocommit=True)
        pol = config.testing_securitypolicy(
            'user', ('group1', 'group2'),
            permissive=False, remember_result=True)
        request = DummyRequest()
        request.registry = config.registry
        val = remember(request, 'fred')
        self.assertEqual(pol.remembered, 'fred')
        self.assertEqual(val, True)

    def test_testing_securitypolicy_forget_result(self):
        from pyramid.security import forget
        config = self._makeOne(autocommit=True)
        pol = config.testing_securitypolicy(
            'user', ('group1', 'group2'),
            permissive=False, forget_result=True)
        request = DummyRequest()
        request.registry = config.registry
        val = forget(request)
        self.assertEqual(pol.forgotten, True)
        self.assertEqual(val, True)

    def test_testing_resources(self):
        from pyramid.traversal import find_resource
        from pyramid.interfaces import ITraverser
        ob1 = object()
        ob2 = object()
        resources = {'/ob1':ob1, '/ob2':ob2}
        config = self._makeOne(autocommit=True)
        config.testing_resources(resources)
        adapter = config.registry.getAdapter(None, ITraverser)
        result = adapter(DummyRequest({'PATH_INFO':'/ob1'}))
        self.assertEqual(result['context'], ob1)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], (text_('ob1'),))
        self.assertEqual(result['virtual_root'], ob1)
        self.assertEqual(result['virtual_root_path'], ())
        result = adapter(DummyRequest({'PATH_INFO':'/ob2'}))
        self.assertEqual(result['context'], ob2)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], (text_('ob2'),))
        self.assertEqual(result['virtual_root'], ob2)
        self.assertEqual(result['virtual_root_path'], ())
        self.assertRaises(KeyError, adapter, DummyRequest({'PATH_INFO':'/ob3'}))
        try:
            config.begin()
            self.assertEqual(find_resource(None, '/ob1'), ob1)
        finally:
            config.end()

    def test_testing_add_subscriber_single(self):
        config = self._makeOne(autocommit=True)
        L = config.testing_add_subscriber(IDummy)
        event = DummyEvent()
        config.registry.notify(event)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.notify(object())
        self.assertEqual(len(L), 1)

    def test_testing_add_subscriber_dottedname(self):
        config = self._makeOne(autocommit=True)
        L = config.testing_add_subscriber(
            'pyramid.tests.test_config.test_init.IDummy')
        event = DummyEvent()
        config.registry.notify(event)
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0], event)
        config.registry.notify(object())
        self.assertEqual(len(L), 1)

    def test_testing_add_subscriber_multiple(self):
        from zope.interface import Interface
        config = self._makeOne(autocommit=True)
        L = config.testing_add_subscriber((Interface, IDummy))
        event = DummyEvent()
        event.object = 'foo'
        # the below is the equivalent of z.c.event.objectEventNotify(event)
        config.registry.subscribers((event.object, event), None)
        self.assertEqual(len(L), 2)
        self.assertEqual(L[0], 'foo')
        self.assertEqual(L[1], event)

    def test_testing_add_subscriber_defaults(self):
        config = self._makeOne(autocommit=True)
        L = config.testing_add_subscriber()
        event = object()
        config.registry.notify(event)
        self.assertEqual(L[-1], event)
        event2 = object()
        config.registry.notify(event2)
        self.assertEqual(L[-1], event2)

    def test_testing_add_renderer(self):
        config = self._makeOne(autocommit=True)
        renderer = config.testing_add_renderer('templates/foo.pt')
        from pyramid.testing import DummyTemplateRenderer
        self.assertTrue(isinstance(renderer, DummyTemplateRenderer))
        from pyramid.renderers import render_to_response
        # must provide request to pass in registry (this is a functest)
        request = DummyRequest()
        request.registry = config.registry
        render_to_response(
            'templates/foo.pt', {'foo':1, 'bar':2}, request=request)
        renderer.assert_(foo=1)
        renderer.assert_(bar=2)
        renderer.assert_(request=request)

    def test_testing_add_renderer_twice(self):
        config = self._makeOne(autocommit=True)
        renderer1 = config.testing_add_renderer('templates/foo.pt')
        renderer2 = config.testing_add_renderer('templates/bar.pt')
        from pyramid.testing import DummyTemplateRenderer
        self.assertTrue(isinstance(renderer1, DummyTemplateRenderer))
        self.assertTrue(isinstance(renderer2, DummyTemplateRenderer))
        from pyramid.renderers import render_to_response
        # must provide request to pass in registry (this is a functest)
        request = DummyRequest()
        request.registry = config.registry
        render_to_response(
            'templates/foo.pt', {'foo':1, 'bar':2}, request=request)
        renderer1.assert_(foo=1)
        renderer1.assert_(bar=2)
        renderer1.assert_(request=request)
        render_to_response(
            'templates/bar.pt', {'foo':1, 'bar':2}, request=request)
        renderer2.assert_(foo=1)
        renderer2.assert_(bar=2)
        renderer2.assert_(request=request)

    def test_testing_add_renderer_explicitrenderer(self):
        config = self._makeOne(autocommit=True)
        class E(Exception): pass
        def renderer(kw, system):
            self.assertEqual(kw, {'foo':1, 'bar':2})
            raise E
        renderer = config.testing_add_renderer('templates/foo.pt', renderer)
        from pyramid.renderers import render_to_response
        # must provide request to pass in registry (this is a functest)
        request = DummyRequest()
        request.registry = config.registry
        try:
            render_to_response(
                'templates/foo.pt', {'foo':1, 'bar':2}, request=request)
        except E:
            pass
        else: # pragma: no cover
            raise AssertionError

    def test_testing_add_template(self):
        config = self._makeOne(autocommit=True)
        renderer = config.testing_add_template('templates/foo.pt')
        from pyramid.testing import DummyTemplateRenderer
        self.assertTrue(isinstance(renderer, DummyTemplateRenderer))
        from pyramid.renderers import render_to_response
        # must provide request to pass in registry (this is a functest)
        request = DummyRequest()
        request.registry = config.registry
        render_to_response('templates/foo.pt', dict(foo=1, bar=2),
                           request=request)
        renderer.assert_(foo=1)
        renderer.assert_(bar=2)
        renderer.assert_(request=request)

from zope.interface import implementer
@implementer(IDummy)
class DummyEvent:
    pass

class DummyRequest(AuthenticationAPIMixin, AuthorizationAPIMixin):
    def __init__(self, environ=None):
        if environ is None:
            environ = {}
        self.environ = environ
        
