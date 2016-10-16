import unittest

from pyramid import testing

class TestAllPermissionsList(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _getTargetClass(self):
        from pyramid.security import AllPermissionsList
        return AllPermissionsList

    def _makeOne(self):
        return self._getTargetClass()()

    def test_it(self):
        thing = self._makeOne()
        self.assertTrue(thing.__eq__(thing))
        self.assertEqual(thing.__iter__(), ())
        self.assertTrue('anything' in thing)

    def test_singleton(self):
        from pyramid.security import ALL_PERMISSIONS
        self.assertEqual(ALL_PERMISSIONS.__class__, self._getTargetClass())

class TestAllowed(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.security import Allowed
        return Allowed
    
    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_it(self):
        allowed = self._makeOne('hello')
        self.assertEqual(allowed.msg, 'hello')
        self.assertEqual(allowed, True)
        self.assertTrue(allowed)
        self.assertEqual(str(allowed), 'hello')
        self.assertTrue('<Allowed instance at ' in repr(allowed))
        self.assertTrue("with msg 'hello'>" in repr(allowed))

class TestDenied(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.security import Denied
        return Denied
    
    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_it(self):
        denied = self._makeOne('hello')
        self.assertEqual(denied.msg, 'hello')
        self.assertEqual(denied, False)
        self.assertFalse(denied)
        self.assertEqual(str(denied), 'hello')
        self.assertTrue('<Denied instance at ' in repr(denied))
        self.assertTrue("with msg 'hello'>" in repr(denied))

class TestACLAllowed(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.security import ACLAllowed
        return ACLAllowed
    
    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_it(self):
        msg = ("ACLAllowed permission 'permission' via ACE 'ace' in ACL 'acl' "
               "on context 'ctx' for principals 'principals'")
        allowed = self._makeOne('ace', 'acl', 'permission', 'principals', 'ctx')
        self.assertTrue(msg in allowed.msg)
        self.assertEqual(allowed, True)
        self.assertTrue(allowed)
        self.assertEqual(str(allowed), msg)
        self.assertTrue('<ACLAllowed instance at ' in repr(allowed))
        self.assertTrue("with msg %r>" % msg in repr(allowed))

class TestACLDenied(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.security import ACLDenied
        return ACLDenied
    
    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_it(self):
        msg = ("ACLDenied permission 'permission' via ACE 'ace' in ACL 'acl' "
               "on context 'ctx' for principals 'principals'")
        denied = self._makeOne('ace', 'acl', 'permission', 'principals', 'ctx')
        self.assertTrue(msg in denied.msg)
        self.assertEqual(denied, False)
        self.assertFalse(denied)
        self.assertEqual(str(denied), msg)
        self.assertTrue('<ACLDenied instance at ' in repr(denied))
        self.assertTrue("with msg %r>" % msg in repr(denied))

class TestPrincipalsAllowedByPermission(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, *arg):
        from pyramid.security import principals_allowed_by_permission
        return principals_allowed_by_permission(*arg)

    def test_no_authorization_policy(self):
        from pyramid.security import Everyone
        context = DummyContext()
        result = self._callFUT(context, 'view')
        self.assertEqual(result, [Everyone])

    def test_with_authorization_policy(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        _registerAuthorizationPolicy(registry, 'yo')
        context = DummyContext()
        result = self._callFUT(context, 'view')
        self.assertEqual(result, 'yo')

class TestRemember(unittest.TestCase):
    def setUp(self):
        testing.setUp()
        
    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, *arg, **kwarg):
        from pyramid.security import remember
        return remember(*arg, **kwarg)

    def test_no_authentication_policy(self):
        request = _makeRequest()
        result = self._callFUT(request, 'me')
        self.assertEqual(result, [])

    def test_with_authentication_policy(self):
        request = _makeRequest()
        registry = request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        result = self._callFUT(request, 'me')
        self.assertEqual(result, [('X-Pyramid-Test', 'me')])

    def test_with_authentication_policy_no_reg_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = _makeRequest()
        del request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        result = self._callFUT(request, 'me')
        self.assertEqual(result, [('X-Pyramid-Test', 'me')])

    def test_with_deprecated_principal_arg(self):
        request = _makeRequest()
        registry = request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        result = self._callFUT(request, principal='me')
        self.assertEqual(result, [('X-Pyramid-Test', 'me')])

    def test_with_missing_arg(self):
        request = _makeRequest()
        registry = request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        self.assertRaises(TypeError, lambda: self._callFUT(request))

class TestForget(unittest.TestCase):
    def setUp(self):
        testing.setUp()
        
    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, *arg):
        from pyramid.security import forget
        return forget(*arg)

    def test_no_authentication_policy(self):
        request = _makeRequest()
        result = self._callFUT(request)
        self.assertEqual(result, [])

    def test_with_authentication_policy(self):
        request = _makeRequest()
        _registerAuthenticationPolicy(request.registry, 'yo')
        result = self._callFUT(request)
        self.assertEqual(result, [('X-Pyramid-Test', 'logout')])

    def test_with_authentication_policy_no_reg_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = _makeRequest()
        del request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        result = self._callFUT(request)
        self.assertEqual(result, [('X-Pyramid-Test', 'logout')])
        
class TestViewExecutionPermitted(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
    
    def _callFUT(self, *arg, **kw):
        from pyramid.security import view_execution_permitted
        return view_execution_permitted(*arg, **kw)

    def _registerSecuredView(self, view_name, allow=True):
        from pyramid.threadlocal import get_current_registry
        from zope.interface import Interface
        from pyramid.interfaces import ISecuredView
        from pyramid.interfaces import IViewClassifier
        class Checker(object):
            def __permitted__(self, context, request):
                self.context = context
                self.request = request
                return allow
        checker = Checker()
        reg = get_current_registry()
        reg.registerAdapter(checker, (IViewClassifier, Interface, Interface),
                            ISecuredView, view_name)
        return checker

    def test_no_permission(self):
        from zope.interface import Interface
        from pyramid.threadlocal import get_current_registry
        from pyramid.interfaces import ISettings
        from pyramid.interfaces import IView
        from pyramid.interfaces import IViewClassifier
        settings = dict(debug_authorization=True)
        reg = get_current_registry()
        reg.registerUtility(settings, ISettings)
        context = DummyContext()
        request = testing.DummyRequest({})
        class DummyView(object):
            pass
        view = DummyView()
        reg.registerAdapter(view, (IViewClassifier, Interface, Interface),
                            IView, '')
        result = self._callFUT(context, request, '')
        msg = result.msg
        self.assertTrue("Allowed: view name '' in context" in msg)
        self.assertTrue('(no permission defined)' in msg)
        self.assertEqual(result, True)

    def test_no_view_registered(self):
        from pyramid.threadlocal import get_current_registry
        from pyramid.interfaces import ISettings
        settings = dict(debug_authorization=True)
        reg = get_current_registry()
        reg.registerUtility(settings, ISettings)
        context = DummyContext()
        request = testing.DummyRequest({})
        self.assertRaises(TypeError, self._callFUT, context, request, '')

    def test_with_permission(self):
        from zope.interface import Interface
        from zope.interface import directlyProvides
        from pyramid.interfaces import IRequest
        class IContext(Interface):
            pass
        context = DummyContext()
        directlyProvides(context, IContext)
        self._registerSecuredView('', True)
        request = testing.DummyRequest({})
        directlyProvides(request, IRequest)
        result = self._callFUT(context, request, '')
        self.assertTrue(result)

class TestAuthenticatedUserId(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def test_backward_compat_delegates_to_mixin(self):
        from zope.deprecation import __show__
        try:
            __show__.off()
            request = _makeFakeRequest()
            from pyramid.security import authenticated_userid
            self.assertEqual(
                authenticated_userid(request),
                'authenticated_userid'
                )
        finally:
            __show__.on()

    def test_no_authentication_policy(self):
        request = _makeRequest()
        self.assertEqual(request.authenticated_userid, None)

    def test_with_authentication_policy(self):
        request = _makeRequest()
        _registerAuthenticationPolicy(request.registry, 'yo')
        self.assertEqual(request.authenticated_userid, 'yo')

    def test_with_authentication_policy_no_reg_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = _makeRequest()
        del request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        self.assertEqual(request.authenticated_userid, 'yo')

class TestUnAuthenticatedUserId(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def test_backward_compat_delegates_to_mixin(self):
        from zope.deprecation import __show__
        try:
            __show__.off()
            request = _makeFakeRequest()
            from pyramid.security import unauthenticated_userid
            self.assertEqual(
                unauthenticated_userid(request),
                'unauthenticated_userid',
                )
        finally:
            __show__.on()

    def test_no_authentication_policy(self):
        request = _makeRequest()
        self.assertEqual(request.unauthenticated_userid, None)

    def test_with_authentication_policy(self):
        request = _makeRequest()
        _registerAuthenticationPolicy(request.registry, 'yo')
        self.assertEqual(request.unauthenticated_userid, 'yo')

    def test_with_authentication_policy_no_reg_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = _makeRequest()
        del request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        self.assertEqual(request.unauthenticated_userid, 'yo')

class TestEffectivePrincipals(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()
        
    def test_backward_compat_delegates_to_mixin(self):
        request = _makeFakeRequest()
        from zope.deprecation import __show__
        try:
            __show__.off()
            from pyramid.security import effective_principals
            self.assertEqual(
                effective_principals(request),
                'effective_principals'
                )
        finally:
            __show__.on()

    def test_no_authentication_policy(self):
        from pyramid.security import Everyone
        request = _makeRequest()
        self.assertEqual(request.effective_principals, [Everyone])

    def test_with_authentication_policy(self):
        request = _makeRequest()
        _registerAuthenticationPolicy(request.registry, 'yo')
        self.assertEqual(request.effective_principals, 'yo')

    def test_with_authentication_policy_no_reg_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = _makeRequest()
        del request.registry
        _registerAuthenticationPolicy(registry, 'yo')
        self.assertEqual(request.effective_principals, 'yo')

class TestHasPermission(unittest.TestCase):
    def setUp(self):
        testing.setUp()
        
    def tearDown(self):
        testing.tearDown()

    def _makeOne(self):
        from pyramid.security import AuthorizationAPIMixin
        from pyramid.registry import Registry
        mixin = AuthorizationAPIMixin()
        mixin.registry = Registry()
        mixin.context = object()
        return mixin

    def test_delegates_to_mixin(self):
        from zope.deprecation import __show__
        try:
            __show__.off()
            mixin = self._makeOne()
            from pyramid.security import has_permission
            self.called_has_permission = False

            def mocked_has_permission(*args, **kw):
                self.called_has_permission = True

            mixin.has_permission = mocked_has_permission
            has_permission('view', object(), mixin)
            self.assertTrue(self.called_has_permission)
        finally:
            __show__.on()

    def test_no_authentication_policy(self):
        request = self._makeOne()
        result = request.has_permission('view')
        self.assertTrue(result)
        self.assertEqual(result.msg, 'No authentication policy in use.')

    def test_with_no_authorization_policy(self):
        request = self._makeOne()
        _registerAuthenticationPolicy(request.registry, None)
        self.assertRaises(ValueError,
                          request.has_permission, 'view', context=None)

    def test_with_authn_and_authz_policies_registered(self):
        request = self._makeOne()
        _registerAuthenticationPolicy(request.registry, None)
        _registerAuthorizationPolicy(request.registry, 'yo')
        self.assertEqual(request.has_permission('view', context=None), 'yo')

    def test_with_no_reg_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = self._makeOne()
        del request.registry
        _registerAuthenticationPolicy(registry, None)
        _registerAuthorizationPolicy(registry, 'yo')
        self.assertEqual(request.has_permission('view'), 'yo')

    def test_with_no_context_passed(self):
        request = self._makeOne()
        self.assertTrue(request.has_permission('view'))

    def test_with_no_context_passed_or_on_request(self):
        request = self._makeOne()
        del request.context
        self.assertRaises(AttributeError, request.has_permission, 'view')

_TEST_HEADER = 'X-Pyramid-Test'

class DummyContext:
    def __init__(self, *arg, **kw):
        self.__dict__.update(kw)

class DummyAuthenticationPolicy:
    def __init__(self, result):
        self.result = result

    def effective_principals(self, request):
        return self.result

    def unauthenticated_userid(self, request):
        return self.result

    def authenticated_userid(self, request):
        return self.result

    def remember(self, request, userid, **kw):
        headers = [(_TEST_HEADER, userid)]
        self._header_remembered = headers[0]
        return headers

    def forget(self, request):
        headers = [(_TEST_HEADER, 'logout')]
        self._header_forgotten = headers[0]
        return headers

class DummyAuthorizationPolicy:
    def __init__(self, result):
        self.result = result

    def permits(self, context, principals, permission):
        return self.result

    def principals_allowed_by_permission(self, context, permission):
        return self.result

def _registerAuthenticationPolicy(reg, result):
    from pyramid.interfaces import IAuthenticationPolicy
    policy = DummyAuthenticationPolicy(result)
    reg.registerUtility(policy, IAuthenticationPolicy)
    return policy

def _registerAuthorizationPolicy(reg, result):
    from pyramid.interfaces import IAuthorizationPolicy
    policy = DummyAuthorizationPolicy(result)
    reg.registerUtility(policy, IAuthorizationPolicy)
    return policy

def _makeRequest():
    from pyramid.registry import Registry
    request = testing.DummyRequest(environ={})
    request.registry = Registry()
    request.context = object()
    return request

def _makeFakeRequest():
    class FakeRequest(testing.DummyRequest):
        @property
        def authenticated_userid(req):
            return 'authenticated_userid'

        @property
        def unauthenticated_userid(req):
            return 'unauthenticated_userid'

        @property
        def effective_principals(req):
            return 'effective_principals'

    return FakeRequest({})

