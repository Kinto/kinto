import unittest
import warnings
from pyramid import testing
from pyramid.compat import (
    text_,
    bytes_,
    )

class TestCallbackAuthenticationPolicyDebugging(unittest.TestCase):
    def setUp(self):
        from pyramid.interfaces import IDebugLogger
        self.config = testing.setUp()
        self.config.registry.registerUtility(self, IDebugLogger)
        self.messages = []

    def tearDown(self):
        del self.config

    def debug(self, msg):
        self.messages.append(msg)

    def _makeOne(self, userid=None, callback=None):
        from pyramid.authentication import CallbackAuthenticationPolicy
        class MyAuthenticationPolicy(CallbackAuthenticationPolicy):
            def unauthenticated_userid(self, request):
                return userid
        policy = MyAuthenticationPolicy()
        policy.debug = True
        policy.callback = callback
        return policy

    def test_authenticated_userid_no_unauthenticated_userid(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            'pyramid.tests.test_authentication.MyAuthenticationPolicy.'
            'authenticated_userid: call to unauthenticated_userid returned '
            'None; returning None')

    def test_authenticated_userid_no_callback(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne(userid='fred')
        self.assertEqual(policy.authenticated_userid(request), 'fred')
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
             "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "authenticated_userid: there was no groupfinder callback; "
            "returning 'fred'")

    def test_authenticated_userid_with_callback_fail(self):
        request = DummyRequest(registry=self.config.registry)
        def callback(userid, request):
            return None
        policy = self._makeOne(userid='fred', callback=callback)
        self.assertEqual(policy.authenticated_userid(request), None)
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            'pyramid.tests.test_authentication.MyAuthenticationPolicy.'
            'authenticated_userid: groupfinder callback returned None; '
            'returning None')

    def test_authenticated_userid_with_callback_success(self):
        request = DummyRequest(registry=self.config.registry)
        def callback(userid, request):
            return []
        policy = self._makeOne(userid='fred', callback=callback)
        self.assertEqual(policy.authenticated_userid(request), 'fred')
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "authenticated_userid: groupfinder callback returned []; "
            "returning 'fred'")

    def test_authenticated_userid_fails_cleaning_as_Authenticated(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne(userid='system.Authenticated')
        self.assertEqual(policy.authenticated_userid(request), None)
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "authenticated_userid: use of userid 'system.Authenticated' is "
            "disallowed by any built-in Pyramid security policy, returning "
            "None")

    def test_authenticated_userid_fails_cleaning_as_Everyone(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne(userid='system.Everyone')
        self.assertEqual(policy.authenticated_userid(request), None)
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "authenticated_userid: use of userid 'system.Everyone' is "
            "disallowed by any built-in Pyramid security policy, returning "
            "None")

    def test_effective_principals_no_unauthenticated_userid(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request),
                         ['system.Everyone'])
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "effective_principals: unauthenticated_userid returned None; "
            "returning ['system.Everyone']")

    def test_effective_principals_no_callback(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne(userid='fred')
        self.assertEqual(
            policy.effective_principals(request),
            ['system.Everyone', 'system.Authenticated', 'fred'])
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(
            self.messages[0],
            'pyramid.tests.test_authentication.MyAuthenticationPolicy.'
            'effective_principals: groupfinder callback is None, so groups '
            'is []')
        self.assertEqual(
            self.messages[1],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "effective_principals: returning effective principals: "
            "['system.Everyone', 'system.Authenticated', 'fred']")

    def test_effective_principals_with_callback_fail(self):
        request = DummyRequest(registry=self.config.registry)
        def callback(userid, request):
            return None
        policy = self._makeOne(userid='fred', callback=callback)
        self.assertEqual(
            policy.effective_principals(request), ['system.Everyone'])
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(
            self.messages[0],
            'pyramid.tests.test_authentication.MyAuthenticationPolicy.'
            'effective_principals: groupfinder callback returned None as '
            'groups')
        self.assertEqual(
            self.messages[1],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "effective_principals: returning effective principals: "
            "['system.Everyone']")

    def test_effective_principals_with_callback_success(self):
        request = DummyRequest(registry=self.config.registry)
        def callback(userid, request):
            return []
        policy = self._makeOne(userid='fred', callback=callback)
        self.assertEqual(
            policy.effective_principals(request),
            ['system.Everyone', 'system.Authenticated', 'fred'])
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(
            self.messages[0],
            'pyramid.tests.test_authentication.MyAuthenticationPolicy.'
            'effective_principals: groupfinder callback returned [] as groups')
        self.assertEqual(
            self.messages[1],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "effective_principals: returning effective principals: "
            "['system.Everyone', 'system.Authenticated', 'fred']")

    def test_effective_principals_with_unclean_principal_Authenticated(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne(userid='system.Authenticated')
        self.assertEqual(
            policy.effective_principals(request),
            ['system.Everyone'])
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "effective_principals: unauthenticated_userid returned disallowed "
            "'system.Authenticated'; returning ['system.Everyone'] as if it "
            "was None")

    def test_effective_principals_with_unclean_principal_Everyone(self):
        request = DummyRequest(registry=self.config.registry)
        policy = self._makeOne(userid='system.Everyone')
        self.assertEqual(
            policy.effective_principals(request),
            ['system.Everyone'])
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0],
            "pyramid.tests.test_authentication.MyAuthenticationPolicy."
            "effective_principals: unauthenticated_userid returned disallowed "
            "'system.Everyone'; returning ['system.Everyone'] as if it "
            "was None")

class TestRepozeWho1AuthenticationPolicy(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.authentication import RepozeWho1AuthenticationPolicy
        return RepozeWho1AuthenticationPolicy

    def _makeOne(self, identifier_name='auth_tkt', callback=None):
        return self._getTargetClass()(identifier_name, callback)

    def test_class_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IAuthenticationPolicy
        verifyClass(IAuthenticationPolicy, self._getTargetClass())

    def test_instance_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IAuthenticationPolicy
        verifyObject(IAuthenticationPolicy, self._makeOne())

    def test_unauthenticated_userid_returns_None(self):
        request = DummyRequest({})
        policy = self._makeOne()
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_userid(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred'}})
        policy = self._makeOne()
        self.assertEqual(policy.unauthenticated_userid(request), 'fred')

    def test_authenticated_userid_None(self):
        request = DummyRequest({})
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred'}})
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), 'fred')

    def test_authenticated_userid_repoze_who_userid_is_None(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':None}})
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid_with_callback_returns_None(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred'}})
        def callback(identity, request):
            return None
        policy = self._makeOne(callback=callback)
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid_with_callback_returns_something(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred'}})
        def callback(identity, request):
            return ['agroup']
        policy = self._makeOne(callback=callback)
        self.assertEqual(policy.authenticated_userid(request), 'fred')

    def test_authenticated_userid_unclean_principal_Authenticated(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'system.Authenticated'}}
            )
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid_unclean_principal_Everyone(self):
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'system.Everyone'}}
            )
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_effective_principals_None(self):
        from pyramid.security import Everyone
        request = DummyRequest({})
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals_userid_only(self):
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred'}})
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request),
                         [Everyone, Authenticated, 'fred'])

    def test_effective_principals_userid_and_groups(self):
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred',
                                    'groups':['quux', 'biz']}})
        def callback(identity, request):
            return identity['groups']
        policy = self._makeOne(callback=callback)
        self.assertEqual(policy.effective_principals(request),
                         [Everyone, Authenticated, 'fred', 'quux', 'biz'])

    def test_effective_principals_userid_callback_returns_None(self):
        from pyramid.security import Everyone
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'fred',
                                    'groups':['quux', 'biz']}})
        def callback(identity, request):
            return None
        policy = self._makeOne(callback=callback)
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals_repoze_who_userid_is_None(self):
        from pyramid.security import Everyone
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':None}}
            )
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals_repoze_who_userid_is_unclean_Everyone(self):
        from pyramid.security import Everyone
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'system.Everyone'}}
            )
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals_repoze_who_userid_is_unclean_Authenticated(
        self):
        from pyramid.security import Everyone
        request = DummyRequest(
            {'repoze.who.identity':{'repoze.who.userid':'system.Authenticated'}}
            )
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_remember_no_plugins(self):
        request = DummyRequest({})
        policy = self._makeOne()
        result = policy.remember(request, 'fred')
        self.assertEqual(result, [])

    def test_remember(self):
        authtkt = DummyWhoPlugin()
        request = DummyRequest(
            {'repoze.who.plugins':{'auth_tkt':authtkt}})
        policy = self._makeOne()
        result = policy.remember(request, 'fred')
        self.assertEqual(result[0], request.environ)
        self.assertEqual(result[1], {'repoze.who.userid':'fred'})

    def test_remember_kwargs(self):
        authtkt = DummyWhoPlugin()
        request = DummyRequest(
            {'repoze.who.plugins':{'auth_tkt':authtkt}})
        policy = self._makeOne()
        result = policy.remember(request, 'fred', max_age=23)
        self.assertEqual(result[1], {'repoze.who.userid':'fred', 'max_age': 23})

    def test_forget_no_plugins(self):
        request = DummyRequest({})
        policy = self._makeOne()
        result = policy.forget(request)
        self.assertEqual(result, [])

    def test_forget(self):
        authtkt = DummyWhoPlugin()
        request = DummyRequest(
            {'repoze.who.plugins':{'auth_tkt':authtkt},
             'repoze.who.identity':{'repoze.who.userid':'fred'},
             })
        policy = self._makeOne()
        result = policy.forget(request)
        self.assertEqual(result[0], request.environ)
        self.assertEqual(result[1], request.environ['repoze.who.identity'])

class TestRemoteUserAuthenticationPolicy(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.authentication import RemoteUserAuthenticationPolicy
        return RemoteUserAuthenticationPolicy

    def _makeOne(self, environ_key='REMOTE_USER', callback=None):
        return self._getTargetClass()(environ_key, callback)

    def test_class_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IAuthenticationPolicy
        verifyClass(IAuthenticationPolicy, self._getTargetClass())

    def test_instance_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IAuthenticationPolicy
        verifyObject(IAuthenticationPolicy, self._makeOne())

    def test_unauthenticated_userid_returns_None(self):
        request = DummyRequest({})
        policy = self._makeOne()
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_userid(self):
        request = DummyRequest({'REMOTE_USER':'fred'})
        policy = self._makeOne()
        self.assertEqual(policy.unauthenticated_userid(request), 'fred')

    def test_authenticated_userid_None(self):
        request = DummyRequest({})
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid(self):
        request = DummyRequest({'REMOTE_USER':'fred'})
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), 'fred')

    def test_effective_principals_None(self):
        from pyramid.security import Everyone
        request = DummyRequest({})
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals(self):
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        request = DummyRequest({'REMOTE_USER':'fred'})
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request),
                         [Everyone, Authenticated, 'fred'])

    def test_remember(self):
        request = DummyRequest({'REMOTE_USER':'fred'})
        policy = self._makeOne()
        result = policy.remember(request, 'fred')
        self.assertEqual(result, [])

    def test_forget(self):
        request = DummyRequest({'REMOTE_USER':'fred'})
        policy = self._makeOne()
        result = policy.forget(request)
        self.assertEqual(result, [])

class TestAuthTktAuthenticationPolicy(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.authentication import AuthTktAuthenticationPolicy
        return AuthTktAuthenticationPolicy

    def _makeOne(self, callback, cookieidentity, **kw):
        inst = self._getTargetClass()('secret', callback, **kw)
        inst.cookie = DummyCookieHelper(cookieidentity)
        return inst

    def setUp(self):
        self.warnings = warnings.catch_warnings()
        self.warnings.__enter__()
        warnings.simplefilter('ignore', DeprecationWarning)

    def tearDown(self):
        self.warnings.__exit__(None, None, None)

    def test_allargs(self):
        # pass all known args
        inst = self._getTargetClass()(
            'secret', callback=None, cookie_name=None, secure=False,
            include_ip=False, timeout=None, reissue_time=None,
            hashalg='sha512',
            )
        self.assertEqual(inst.callback, None)

    def test_hashalg_override(self):
        # important to ensure hashalg is passed to cookie helper
        inst = self._getTargetClass()('secret', hashalg='sha512')
        self.assertEqual(inst.cookie.hashalg, 'sha512')

    def test_unauthenticated_userid_returns_None(self):
        request = DummyRequest({})
        policy = self._makeOne(None, None)
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_userid(self):
        request = DummyRequest({'REMOTE_USER':'fred'})
        policy = self._makeOne(None, {'userid':'fred'})
        self.assertEqual(policy.unauthenticated_userid(request), 'fred')

    def test_authenticated_userid_no_cookie_identity(self):
        request = DummyRequest({})
        policy = self._makeOne(None, None)
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid_callback_returns_None(self):
        request = DummyRequest({})
        def callback(userid, request):
            return None
        policy = self._makeOne(callback, {'userid':'fred'})
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid(self):
        request = DummyRequest({})
        def callback(userid, request):
            return True
        policy = self._makeOne(callback, {'userid':'fred'})
        self.assertEqual(policy.authenticated_userid(request), 'fred')

    def test_effective_principals_no_cookie_identity(self):
        from pyramid.security import Everyone
        request = DummyRequest({})
        policy = self._makeOne(None, None)
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals_callback_returns_None(self):
        from pyramid.security import Everyone
        request = DummyRequest({})
        def callback(userid, request):
            return None
        policy = self._makeOne(callback, {'userid':'fred'})
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals(self):
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        request = DummyRequest({})
        def callback(userid, request):
            return ['group.foo']
        policy = self._makeOne(callback, {'userid':'fred'})
        self.assertEqual(policy.effective_principals(request),
                             [Everyone, Authenticated, 'fred', 'group.foo'])

    def test_remember(self):
        request = DummyRequest({})
        policy = self._makeOne(None, None)
        result = policy.remember(request, 'fred')
        self.assertEqual(result, [])

    def test_remember_with_extra_kargs(self):
        request = DummyRequest({})
        policy = self._makeOne(None, None)
        result = policy.remember(request, 'fred', a=1, b=2)
        self.assertEqual(policy.cookie.kw, {'a':1, 'b':2})
        self.assertEqual(result, [])

    def test_forget(self):
        request = DummyRequest({})
        policy = self._makeOne(None, None)
        result = policy.forget(request)
        self.assertEqual(result, [])

    def test_class_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IAuthenticationPolicy
        verifyClass(IAuthenticationPolicy, self._getTargetClass())

    def test_instance_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IAuthenticationPolicy
        verifyObject(IAuthenticationPolicy, self._makeOne(None, None))

class TestAuthTktCookieHelper(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.authentication import AuthTktCookieHelper
        return AuthTktCookieHelper

    def _makeOne(self, *arg, **kw):
        helper = self._getTargetClass()(*arg, **kw)
        # laziness after moving auth_tkt classes and funcs into
        # authentication module
        auth_tkt = DummyAuthTktModule()
        helper.auth_tkt = auth_tkt
        helper.AuthTicket = auth_tkt.AuthTicket
        helper.parse_ticket = auth_tkt.parse_ticket
        helper.BadTicket = auth_tkt.BadTicket
        return helper

    def _makeRequest(self, cookie=None, ipv6=False):
        environ = {'wsgi.version': (1,0)}

        if ipv6 is False:
            environ['REMOTE_ADDR'] = '1.1.1.1'
        else:
            environ['REMOTE_ADDR'] = '::1'
        environ['SERVER_NAME'] = 'localhost'
        return DummyRequest(environ, cookie=cookie)

    def _cookieValue(self, cookie):
        items = cookie.value.split('/')
        D = {}
        for item in items:
            k, v = item.split('=', 1)
            D[k] = v
        return D

    def _parseHeaders(self, headers):
        return [ self._parseHeader(header) for header in headers ]

    def _parseHeader(self, header):
        cookie = self._parseCookie(header[1])
        return cookie

    def _parseCookie(self, cookie):
        from pyramid.compat import SimpleCookie
        cookies = SimpleCookie()
        cookies.load(cookie)
        return cookies.get('auth_tkt')

    def test_identify_nocookie(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.identify(request)
        self.assertEqual(result, None)

    def test_identify_cookie_value_is_None(self):
        helper = self._makeOne('secret')
        request = self._makeRequest(None)
        result = helper.identify(request)
        self.assertEqual(result, None)

    def test_identify_good_cookie_include_ip(self):
        helper = self._makeOne('secret', include_ip=True)
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], 'userid')
        self.assertEqual(result['userdata'], '')
        self.assertEqual(result['timestamp'], 0)
        self.assertEqual(helper.auth_tkt.value, 'ticket')
        self.assertEqual(helper.auth_tkt.remote_addr, '1.1.1.1')
        self.assertEqual(helper.auth_tkt.secret, 'secret')
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_include_ipv6(self):
        helper = self._makeOne('secret', include_ip=True)
        request = self._makeRequest('ticket', ipv6=True)
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], 'userid')
        self.assertEqual(result['userdata'], '')
        self.assertEqual(result['timestamp'], 0)
        self.assertEqual(helper.auth_tkt.value, 'ticket')
        self.assertEqual(helper.auth_tkt.remote_addr, '::1')
        self.assertEqual(helper.auth_tkt.secret, 'secret')
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_dont_include_ip(self):
        helper = self._makeOne('secret', include_ip=False)
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], 'userid')
        self.assertEqual(result['userdata'], '')
        self.assertEqual(result['timestamp'], 0)
        self.assertEqual(helper.auth_tkt.value, 'ticket')
        self.assertEqual(helper.auth_tkt.remote_addr, '0.0.0.0')
        self.assertEqual(helper.auth_tkt.secret, 'secret')
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_int_useridtype(self):
        helper = self._makeOne('secret', include_ip=False)
        helper.auth_tkt.userid = '1'
        helper.auth_tkt.user_data = 'userid_type:int'
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], 1)
        self.assertEqual(result['userdata'], 'userid_type:int')
        self.assertEqual(result['timestamp'], 0)
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'userid_type:int')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_nonuseridtype_user_data(self):
        helper = self._makeOne('secret', include_ip=False)
        helper.auth_tkt.userid = '1'
        helper.auth_tkt.user_data = 'bogus:int'
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], '1')
        self.assertEqual(result['userdata'], 'bogus:int')
        self.assertEqual(result['timestamp'], 0)
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'bogus:int')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_unknown_useridtype(self):
        helper = self._makeOne('secret', include_ip=False)
        helper.auth_tkt.userid = 'abc'
        helper.auth_tkt.user_data = 'userid_type:unknown'
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], 'abc')
        self.assertEqual(result['userdata'], 'userid_type:unknown')
        self.assertEqual(result['timestamp'], 0)
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'userid_type:unknown')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_b64str_useridtype(self):
        from base64 import b64encode
        helper = self._makeOne('secret', include_ip=False)
        helper.auth_tkt.userid = b64encode(b'encoded').strip()
        helper.auth_tkt.user_data = 'userid_type:b64str'
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], b'encoded')
        self.assertEqual(result['userdata'], 'userid_type:b64str')
        self.assertEqual(result['timestamp'], 0)
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'userid_type:b64str')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_b64unicode_useridtype(self):
        from base64 import b64encode
        helper = self._makeOne('secret', include_ip=False)
        helper.auth_tkt.userid = b64encode(b'\xc3\xa9ncoded').strip()
        helper.auth_tkt.user_data = 'userid_type:b64unicode'
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], ())
        self.assertEqual(result['userid'], text_(b'\xc3\xa9ncoded', 'utf-8'))
        self.assertEqual(result['userdata'], 'userid_type:b64unicode')
        self.assertEqual(result['timestamp'], 0)
        environ = request.environ
        self.assertEqual(environ['REMOTE_USER_TOKENS'], ())
        self.assertEqual(environ['REMOTE_USER_DATA'],'userid_type:b64unicode')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_bad_cookie(self):
        helper = self._makeOne('secret', include_ip=True)
        helper.auth_tkt.parse_raise = True
        request = self._makeRequest('ticket')
        result = helper.identify(request)
        self.assertEqual(result, None)

    def test_identify_cookie_timed_out(self):
        helper = self._makeOne('secret', timeout=1)
        request = self._makeRequest({'HTTP_COOKIE':'auth_tkt=bogus'})
        result = helper.identify(request)
        self.assertEqual(result, None)

    def test_identify_cookie_reissue(self):
        import time
        helper = self._makeOne('secret', timeout=10, reissue_time=0)
        now = time.time()
        helper.auth_tkt.timestamp = now
        helper.now = now + 1
        helper.auth_tkt.tokens = (text_('a'), )
        request = self._makeRequest('bogus')
        result = helper.identify(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 1)
        response = DummyResponse()
        request.callbacks[0](request, response)
        self.assertEqual(len(response.headerlist), 3)
        self.assertEqual(response.headerlist[0][0], 'Set-Cookie')

    def test_identify_cookie_reissue_already_reissued_this_request(self):
        import time
        helper = self._makeOne('secret', timeout=10, reissue_time=0)
        now = time.time()
        helper.auth_tkt.timestamp = now
        helper.now = now + 1
        request = self._makeRequest('bogus')
        request._authtkt_reissued = True
        result = helper.identify(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 0)

    def test_identify_cookie_reissue_notyet(self):
        import time
        helper = self._makeOne('secret', timeout=10, reissue_time=10)
        now = time.time()
        helper.auth_tkt.timestamp = now
        helper.now = now + 1
        request = self._makeRequest('bogus')
        result = helper.identify(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 0)

    def test_identify_cookie_reissue_revoked_by_forget(self):
        import time
        helper = self._makeOne('secret', timeout=10, reissue_time=0)
        now = time.time()
        helper.auth_tkt.timestamp = now
        helper.now = now + 1
        request = self._makeRequest('bogus')
        result = helper.identify(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 1)
        result = helper.forget(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 1)
        response = DummyResponse()
        request.callbacks[0](request, response)
        self.assertEqual(len(response.headerlist), 0)

    def test_identify_cookie_reissue_revoked_by_remember(self):
        import time
        helper = self._makeOne('secret', timeout=10, reissue_time=0)
        now = time.time()
        helper.auth_tkt.timestamp = now
        helper.now = now + 1
        request = self._makeRequest('bogus')
        result = helper.identify(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 1)
        result = helper.remember(request, 'bob')
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 1)
        response = DummyResponse()
        request.callbacks[0](request, response)
        self.assertEqual(len(response.headerlist), 0)

    def test_identify_cookie_reissue_with_tokens_default(self):
        # see https://github.com/Pylons/pyramid/issues#issue/108
        import time
        helper = self._makeOne('secret', timeout=10, reissue_time=0)
        auth_tkt = DummyAuthTktModule(tokens=[''])
        helper.auth_tkt = auth_tkt
        helper.AuthTicket = auth_tkt.AuthTicket
        helper.parse_ticket = auth_tkt.parse_ticket
        helper.BadTicket = auth_tkt.BadTicket
        now = time.time()
        helper.auth_tkt.timestamp = now
        helper.now = now + 1
        request = self._makeRequest('bogus')
        result = helper.identify(request)
        self.assertTrue(result)
        self.assertEqual(len(request.callbacks), 1)
        response = DummyResponse()
        request.callbacks[0](None, response)
        self.assertEqual(len(response.headerlist), 3)
        self.assertEqual(response.headerlist[0][0], 'Set-Cookie')
        self.assertTrue("/tokens=/" in response.headerlist[0][1])

    def test_remember(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.remember(request, 'userid')
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith('; Path=/'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue(result[1][1].endswith('; Domain=localhost; Path=/'))
        self.assertTrue(result[1][1].startswith('auth_tkt='))

        self.assertEqual(result[2][0], 'Set-Cookie')
        self.assertTrue(result[2][1].endswith('; Domain=.localhost; Path=/'))
        self.assertTrue(result[2][1].startswith('auth_tkt='))

    def test_remember_include_ip(self):
        helper = self._makeOne('secret', include_ip=True)
        request = self._makeRequest()
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith('; Path=/'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue(result[1][1].endswith('; Domain=localhost; Path=/'))
        self.assertTrue(result[1][1].startswith('auth_tkt='))

        self.assertEqual(result[2][0], 'Set-Cookie')
        self.assertTrue(result[2][1].endswith('; Domain=.localhost; Path=/'))
        self.assertTrue(result[2][1].startswith('auth_tkt='))

    def test_remember_path(self):
        helper = self._makeOne('secret', include_ip=True,
                               path="/cgi-bin/app.cgi/")
        request = self._makeRequest()
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith('; Path=/cgi-bin/app.cgi/'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue(result[1][1].endswith(
            '; Domain=localhost; Path=/cgi-bin/app.cgi/'))
        self.assertTrue(result[1][1].startswith('auth_tkt='))

        self.assertEqual(result[2][0], 'Set-Cookie')
        self.assertTrue(result[2][1].endswith(
            '; Domain=.localhost; Path=/cgi-bin/app.cgi/'))
        self.assertTrue(result[2][1].startswith('auth_tkt='))

    def test_remember_http_only(self):
        helper = self._makeOne('secret', include_ip=True, http_only=True)
        request = self._makeRequest()
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith('; HttpOnly'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue('; HttpOnly' in result[1][1])
        self.assertTrue(result[1][1].startswith('auth_tkt='))

        self.assertEqual(result[2][0], 'Set-Cookie')
        self.assertTrue('; HttpOnly' in result[2][1])
        self.assertTrue(result[2][1].startswith('auth_tkt='))

    def test_remember_secure(self):
        helper = self._makeOne('secret', include_ip=True, secure=True)
        request = self._makeRequest()
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue('; secure' in result[0][1])
        self.assertTrue(result[0][1].startswith('auth_tkt='))

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue('; secure' in result[1][1])
        self.assertTrue(result[1][1].startswith('auth_tkt='))

        self.assertEqual(result[2][0], 'Set-Cookie')
        self.assertTrue('; secure' in result[2][1])
        self.assertTrue(result[2][1].startswith('auth_tkt='))

    def test_remember_wild_domain_disabled(self):
        helper = self._makeOne('secret', wild_domain=False)
        request = self._makeRequest()
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith('; Path=/'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue(result[1][1].endswith('; Domain=localhost; Path=/'))
        self.assertTrue(result[1][1].startswith('auth_tkt='))

    def test_remember_parent_domain(self):
        helper = self._makeOne('secret', parent_domain=True)
        request = self._makeRequest()
        request.domain = 'www.example.com'
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith('; Domain=.example.com; Path=/'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

    def test_remember_parent_domain_supercedes_wild_domain(self):
        helper = self._makeOne('secret', parent_domain=True, wild_domain=True)
        request = self._makeRequest()
        request.domain = 'www.example.com'
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0][1].endswith('; Domain=.example.com; Path=/'))

    def test_remember_explicit_domain(self):
        helper = self._makeOne('secret', domain='pyramid.bazinga')
        request = self._makeRequest()
        request.domain = 'www.example.com'
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue(result[0][1].endswith(
                '; Domain=pyramid.bazinga; Path=/'))
        self.assertTrue(result[0][1].startswith('auth_tkt='))

    def test_remember_domain_supercedes_parent_and_wild_domain(self):
        helper = self._makeOne('secret', domain='pyramid.bazinga',
                parent_domain=True, wild_domain=True)
        request = self._makeRequest()
        request.domain = 'www.example.com'
        result = helper.remember(request, 'other')
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0][1].endswith(
                '; Domain=pyramid.bazinga; Path=/'))

    def test_remember_binary_userid(self):
        import base64
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.remember(request, b'userid')
        values = self._parseHeaders(result)
        self.assertEqual(len(result), 3)
        val = self._cookieValue(values[0])
        self.assertEqual(val['userid'],
                         text_(base64.b64encode(b'userid').strip()))
        self.assertEqual(val['user_data'], 'userid_type:b64str')

    def test_remember_int_userid(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.remember(request, 1)
        values = self._parseHeaders(result)
        self.assertEqual(len(result), 3)
        val = self._cookieValue(values[0])
        self.assertEqual(val['userid'], '1')
        self.assertEqual(val['user_data'], 'userid_type:int')

    def test_remember_long_userid(self):
        from pyramid.compat import long
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.remember(request, long(1))
        values = self._parseHeaders(result)
        self.assertEqual(len(result), 3)
        val = self._cookieValue(values[0])
        self.assertEqual(val['userid'], '1')
        self.assertEqual(val['user_data'], 'userid_type:int')

    def test_remember_unicode_userid(self):
        import base64
        helper = self._makeOne('secret')
        request = self._makeRequest()
        userid = text_(b'\xc2\xa9', 'utf-8')
        result = helper.remember(request, userid)
        values = self._parseHeaders(result)
        self.assertEqual(len(result), 3)
        val = self._cookieValue(values[0])
        self.assertEqual(val['userid'],
                         text_(base64.b64encode(userid.encode('utf-8'))))
        self.assertEqual(val['user_data'], 'userid_type:b64unicode')

    def test_remember_insane_userid(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        userid = object()
        result = helper.remember(request, userid)
        values = self._parseHeaders(result)
        self.assertEqual(len(result), 3)
        value = values[0]
        self.assertTrue('userid' in value.value)

    def test_remember_max_age(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.remember(request, 'userid', max_age='500')
        values = self._parseHeaders(result)
        self.assertEqual(len(result), 3)

        self.assertEqual(values[0]['max-age'], '500')
        self.assertTrue(values[0]['expires'])

    def test_remember_tokens(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        result = helper.remember(request, 'other', tokens=('foo', 'bar'))
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], 'Set-Cookie')
        self.assertTrue("/tokens=foo|bar/" in result[0][1])

        self.assertEqual(result[1][0], 'Set-Cookie')
        self.assertTrue("/tokens=foo|bar/" in result[1][1])

        self.assertEqual(result[2][0], 'Set-Cookie')
        self.assertTrue("/tokens=foo|bar/" in result[2][1])

    def test_remember_unicode_but_ascii_token(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        la = text_(b'foo', 'utf-8')
        result = helper.remember(request, 'other', tokens=(la,))
        # tokens must be str type on both Python 2 and 3
        self.assertTrue("/tokens=foo/" in result[0][1])

    def test_remember_nonascii_token(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        la = text_(b'La Pe\xc3\xb1a', 'utf-8')
        self.assertRaises(ValueError, helper.remember, request, 'other',
                          tokens=(la,))

    def test_remember_invalid_token_format(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        self.assertRaises(ValueError, helper.remember, request, 'other',
                          tokens=('foo bar',))
        self.assertRaises(ValueError, helper.remember, request, 'other',
                          tokens=('1bar',))

    def test_forget(self):
        helper = self._makeOne('secret')
        request = self._makeRequest()
        headers = helper.forget(request)
        self.assertEqual(len(headers), 3)
        name, value = headers[0]
        self.assertEqual(name, 'Set-Cookie')
        self.assertEqual(
            value,
            'auth_tkt=; Max-Age=0; Path=/; '
            'expires=Wed, 31-Dec-97 23:59:59 GMT'
            )
        name, value = headers[1]
        self.assertEqual(name, 'Set-Cookie')
        self.assertEqual(
            value,
            'auth_tkt=; Domain=localhost; Max-Age=0; Path=/; '
            'expires=Wed, 31-Dec-97 23:59:59 GMT'
            )
        name, value = headers[2]
        self.assertEqual(name, 'Set-Cookie')
        self.assertEqual(
            value,
            'auth_tkt=; Domain=.localhost; Max-Age=0; Path=/; '
            'expires=Wed, 31-Dec-97 23:59:59 GMT'
            )

class TestAuthTicket(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.authentication import AuthTicket
        return AuthTicket(*arg, **kw)

    def test_ctor_with_tokens(self):
        ticket = self._makeOne('secret', 'userid', 'ip', tokens=('a', 'b'))
        self.assertEqual(ticket.tokens, 'a,b')

    def test_ctor_with_time(self):
        ticket = self._makeOne('secret', 'userid', 'ip', time='time')
        self.assertEqual(ticket.time, 'time')

    def test_digest(self):
        ticket = self._makeOne('secret', 'userid', '0.0.0.0', time=10)
        result = ticket.digest()
        self.assertEqual(result, '126fd6224912187ee9ffa80e0b81420c')

    def test_digest_sha512(self):
        ticket = self._makeOne('secret', 'userid', '0.0.0.0',
                               time=10, hashalg='sha512')
        result = ticket.digest()
        self.assertEqual(result, '74770b2e0d5b1a54c2a466ec567a40f7d7823576aa49'\
                                 '3c65fc3445e9b44097f4a80410319ef8cb256a2e60b9'\
                                 'c2002e48a9e33a3e8ee4379352c04ef96d2cb278')

    def test_cookie_value(self):
        ticket = self._makeOne('secret', 'userid', '0.0.0.0', time=10,
                               tokens=('a', 'b'))
        result = ticket.cookie_value()
        self.assertEqual(result,
                         '66f9cc3e423dc57c91df696cf3d1f0d80000000auserid!a,b!')

    def test_ipv4(self):
        ticket = self._makeOne('secret', 'userid', '198.51.100.1',
                               time=10, hashalg='sha256')
        result = ticket.cookie_value()
        self.assertEqual(result, 'b3e7156db4f8abde4439c4a6499a0668f9e7ffd7fa27b'\
                                 '798400ecdade8d76c530000000auserid!')

    def test_ipv6(self):
        ticket = self._makeOne('secret', 'userid', '2001:db8::1',
                               time=10, hashalg='sha256')
        result = ticket.cookie_value()
        self.assertEqual(result, 'd025b601a0f12ca6d008aa35ff3a22b7d8f3d1c1456c8'\
                                 '5becf8760cd7a2fa4910000000auserid!')

class TestBadTicket(unittest.TestCase):
    def _makeOne(self, msg, expected=None):
        from pyramid.authentication import BadTicket
        return BadTicket(msg, expected)

    def test_it(self):
        exc = self._makeOne('msg', expected=True)
        self.assertEqual(exc.expected, True)
        self.assertTrue(isinstance(exc, Exception))

class Test_parse_ticket(unittest.TestCase):
    def _callFUT(self, secret, ticket, ip, hashalg='md5'):
        from pyramid.authentication import parse_ticket
        return parse_ticket(secret, ticket, ip, hashalg)

    def _assertRaisesBadTicket(self, secret, ticket, ip, hashalg='md5'):
        from pyramid.authentication import BadTicket
        self.assertRaises(BadTicket,self._callFUT, secret, ticket, ip, hashalg)

    def test_bad_timestamp(self):
        ticket = 'x' * 64
        self._assertRaisesBadTicket('secret', ticket, 'ip')

    def test_bad_userid_or_data(self):
        ticket = 'x' * 32 + '11111111' + 'x' * 10
        self._assertRaisesBadTicket('secret', ticket, 'ip')

    def test_digest_sig_incorrect(self):
        ticket = 'x' * 32 + '11111111' + 'a!b!c'
        self._assertRaisesBadTicket('secret', ticket, '0.0.0.0')

    def test_correct_with_user_data(self):
        ticket = '66f9cc3e423dc57c91df696cf3d1f0d80000000auserid!a,b!'
        result = self._callFUT('secret', ticket, '0.0.0.0')
        self.assertEqual(result, (10, 'userid', ['a', 'b'], ''))

    def test_correct_with_user_data_sha512(self):
        ticket = '7d947cdef99bad55f8e3382a8bd089bb9dd0547f7925b7d189adc1160cab'\
                 '0ec0e6888faa41eba641a18522b26f19109f3ffafb769767ba8a26d02aae'\
                 'ae56599a0000000auserid!a,b!'
        result = self._callFUT('secret', ticket, '0.0.0.0', 'sha512')
        self.assertEqual(result, (10, 'userid', ['a', 'b'], ''))

    def test_ipv4(self):
        ticket = 'b3e7156db4f8abde4439c4a6499a0668f9e7ffd7fa27b798400ecdade8d7'\
                 '6c530000000auserid!'
        result = self._callFUT('secret', ticket, '198.51.100.1', 'sha256')
        self.assertEqual(result, (10, 'userid', [''], ''))

    def test_ipv6(self):
        ticket = 'd025b601a0f12ca6d008aa35ff3a22b7d8f3d1c1456c85becf8760cd7a2f'\
                 'a4910000000auserid!'
        result = self._callFUT('secret', ticket, '2001:db8::1', 'sha256')
        self.assertEqual(result, (10, 'userid', [''], ''))
        pass

class TestSessionAuthenticationPolicy(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.authentication import SessionAuthenticationPolicy
        return SessionAuthenticationPolicy

    def _makeOne(self, callback=None, prefix=''):
        return self._getTargetClass()(prefix=prefix, callback=callback)

    def test_class_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IAuthenticationPolicy
        verifyClass(IAuthenticationPolicy, self._getTargetClass())

    def test_instance_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IAuthenticationPolicy
        verifyObject(IAuthenticationPolicy, self._makeOne())

    def test_unauthenticated_userid_returns_None(self):
        request = DummyRequest()
        policy = self._makeOne()
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_userid(self):
        request = DummyRequest(session={'userid':'fred'})
        policy = self._makeOne()
        self.assertEqual(policy.unauthenticated_userid(request), 'fred')

    def test_authenticated_userid_no_cookie_identity(self):
        request = DummyRequest()
        policy = self._makeOne()
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid_callback_returns_None(self):
        request = DummyRequest(session={'userid':'fred'})
        def callback(userid, request):
            return None
        policy = self._makeOne(callback)
        self.assertEqual(policy.authenticated_userid(request), None)

    def test_authenticated_userid(self):
        request = DummyRequest(session={'userid':'fred'})
        def callback(userid, request):
            return True
        policy = self._makeOne(callback)
        self.assertEqual(policy.authenticated_userid(request), 'fred')

    def test_effective_principals_no_identity(self):
        from pyramid.security import Everyone
        request = DummyRequest()
        policy = self._makeOne()
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals_callback_returns_None(self):
        from pyramid.security import Everyone
        request = DummyRequest(session={'userid':'fred'})
        def callback(userid, request):
            return None
        policy = self._makeOne(callback)
        self.assertEqual(policy.effective_principals(request), [Everyone])

    def test_effective_principals(self):
        from pyramid.security import Everyone
        from pyramid.security import Authenticated
        request = DummyRequest(session={'userid':'fred'})
        def callback(userid, request):
            return ['group.foo']
        policy = self._makeOne(callback)
        self.assertEqual(policy.effective_principals(request),
                         [Everyone, Authenticated, 'fred', 'group.foo'])

    def test_remember(self):
        request = DummyRequest()
        policy = self._makeOne()
        result = policy.remember(request, 'fred')
        self.assertEqual(request.session.get('userid'), 'fred')
        self.assertEqual(result, [])

    def test_forget(self):
        request = DummyRequest(session={'userid':'fred'})
        policy = self._makeOne()
        result = policy.forget(request)
        self.assertEqual(request.session.get('userid'), None)
        self.assertEqual(result, [])

    def test_forget_no_identity(self):
        request = DummyRequest()
        policy = self._makeOne()
        result = policy.forget(request)
        self.assertEqual(request.session.get('userid'), None)
        self.assertEqual(result, [])

class TestBasicAuthAuthenticationPolicy(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.authentication import BasicAuthAuthenticationPolicy as cls
        return cls

    def _makeOne(self, check):
        return self._getTargetClass()(check, realm='SomeRealm')

    def test_class_implements_IAuthenticationPolicy(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IAuthenticationPolicy
        verifyClass(IAuthenticationPolicy, self._getTargetClass())

    def test_unauthenticated_userid(self):
        import base64
        request = testing.DummyRequest()
        request.headers['Authorization'] = 'Basic %s' % base64.b64encode(
            bytes_('chrisr:password')).decode('ascii')
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), 'chrisr')

    def test_unauthenticated_userid_no_credentials(self):
        request = testing.DummyRequest()
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_bad_header(self):
        request = testing.DummyRequest()
        request.headers['Authorization'] = '...'
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_userid_not_basic(self):
        request = testing.DummyRequest()
        request.headers['Authorization'] = 'Complicated things'
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_unauthenticated_userid_corrupt_base64(self):
        request = testing.DummyRequest()
        request.headers['Authorization'] = 'Basic chrisr:password'
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_authenticated_userid(self):
        import base64
        request = testing.DummyRequest()
        request.headers['Authorization'] = 'Basic %s' % base64.b64encode(
            bytes_('chrisr:password')).decode('ascii')
        def check(username, password, request):
            return []
        policy = self._makeOne(check)
        self.assertEqual(policy.authenticated_userid(request), 'chrisr')

    def test_authenticated_userid_utf8(self):
        import base64
        request = testing.DummyRequest()
        inputs = (b'm\xc3\xb6rk\xc3\xb6:'
                  b'm\xc3\xb6rk\xc3\xb6password').decode('utf-8')
        request.headers['Authorization'] = 'Basic %s' % (
            base64.b64encode(inputs.encode('utf-8')).decode('latin-1'))
        def check(username, password, request):
            return []
        policy = self._makeOne(check)
        self.assertEqual(policy.authenticated_userid(request),
                         b'm\xc3\xb6rk\xc3\xb6'.decode('utf-8'))

    def test_authenticated_userid_latin1(self):
        import base64
        request = testing.DummyRequest()
        inputs = (b'm\xc3\xb6rk\xc3\xb6:'
                  b'm\xc3\xb6rk\xc3\xb6password').decode('utf-8')
        request.headers['Authorization'] = 'Basic %s' % (
            base64.b64encode(inputs.encode('latin-1')).decode('latin-1'))
        def check(username, password, request):
            return []
        policy = self._makeOne(check)
        self.assertEqual(policy.authenticated_userid(request),
                         b'm\xc3\xb6rk\xc3\xb6'.decode('utf-8'))

    def test_unauthenticated_userid_invalid_payload(self):
        import base64
        request = testing.DummyRequest()
        request.headers['Authorization'] = 'Basic %s' % base64.b64encode(
            bytes_('chrisrpassword')).decode('ascii')
        policy = self._makeOne(None)
        self.assertEqual(policy.unauthenticated_userid(request), None)

    def test_remember(self):
        policy = self._makeOne(None)
        self.assertEqual(policy.remember(None, None), [])

    def test_forget(self):
        policy = self._makeOne(None)
        self.assertEqual(policy.forget(None), [
            ('WWW-Authenticate', 'Basic realm="SomeRealm"')])

class TestSimpleSerializer(unittest.TestCase):
    def _makeOne(self):
        from pyramid.authentication import _SimpleSerializer
        return _SimpleSerializer()

    def test_loads(self):
        inst = self._makeOne()
        self.assertEqual(inst.loads(b'abc'), text_('abc'))

    def test_dumps(self):
        inst = self._makeOne()
        self.assertEqual(inst.dumps('abc'), bytes_('abc'))
        
class DummyContext:
    pass

class DummyCookies(object):
    def __init__(self, cookie):
        self.cookie = cookie

    def get(self, name):
        return self.cookie

class DummyRequest:
    domain = 'localhost'
    def __init__(self, environ=None, session=None, registry=None, cookie=None):
        self.environ = environ or {}
        self.session = session or {}
        self.registry = registry
        self.callbacks = []
        self.cookies = DummyCookies(cookie)

    def add_response_callback(self, callback):
        self.callbacks.append(callback)

class DummyWhoPlugin:
    def remember(self, environ, identity):
        return environ, identity

    def forget(self, environ, identity):
        return environ, identity

class DummyCookieHelper:
    def __init__(self, result):
        self.result = result

    def identify(self, *arg, **kw):
        return self.result

    def remember(self, *arg, **kw):
        self.kw = kw
        return []

    def forget(self, *arg):
        return []

class DummyAuthTktModule(object):
    def __init__(self, timestamp=0, userid='userid', tokens=(), user_data='',
                 parse_raise=False, hashalg="md5"):
        self.timestamp = timestamp
        self.userid = userid
        self.tokens = tokens
        self.user_data = user_data
        self.parse_raise = parse_raise
        self.hashalg = hashalg
        def parse_ticket(secret, value, remote_addr, hashalg):
            self.secret = secret
            self.value = value
            self.remote_addr = remote_addr
            if self.parse_raise:
                raise self.BadTicket()
            return self.timestamp, self.userid, self.tokens, self.user_data
        self.parse_ticket = parse_ticket

        class AuthTicket(object):
            def __init__(self, secret, userid, remote_addr, **kw):
                self.secret = secret
                self.userid = userid
                self.remote_addr = remote_addr
                self.kw = kw

            def cookie_value(self):
                result = {
                    'secret':self.secret,
                    'userid':self.userid,
                    'remote_addr':self.remote_addr
                    }
                result.update(self.kw)
                tokens = result.pop('tokens', None)
                if tokens is not None:
                    tokens = '|'.join(tokens)
                    result['tokens'] = tokens
                items = sorted(result.items())
                new_items = []
                for k, v in items:
                    if isinstance(v, bytes):
                        v = text_(v)
                    new_items.append((k,v))
                result = '/'.join(['%s=%s' % (k, v) for k,v in new_items ])
                return result
        self.AuthTicket = AuthTicket

    class BadTicket(Exception):
        pass

class DummyResponse:
    def __init__(self):
        self.headerlist = []

