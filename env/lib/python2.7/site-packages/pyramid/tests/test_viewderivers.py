import unittest
from zope.interface import implementer

from pyramid import testing
from pyramid.exceptions import ConfigurationError
from pyramid.interfaces import (
    IResponse,
    IRequest,
    )

class TestDeriveView(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        self.config = None
        testing.tearDown()

    def _makeRequest(self):
        request = DummyRequest()
        request.registry = self.config.registry
        return request

    def _registerLogger(self):
        from pyramid.interfaces import IDebugLogger
        logger = DummyLogger()
        self.config.registry.registerUtility(logger, IDebugLogger)
        return logger

    def _registerSecurityPolicy(self, permissive):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        policy = DummySecurityPolicy(permissive)
        self.config.registry.registerUtility(policy, IAuthenticationPolicy)
        self.config.registry.registerUtility(policy, IAuthorizationPolicy)

    def test_function_returns_non_adaptable(self):
        def view(request):
            return None
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        try:
            result(None, None)
        except ValueError as e:
            self.assertEqual(
                e.args[0],
                'Could not convert return value of the view callable function '
                'pyramid.tests.test_viewderivers.view into a response '
                'object. The value returned was None. You may have forgotten '
                'to return a value from the view callable.'
                )
        else: # pragma: no cover
            raise AssertionError

    def test_function_returns_non_adaptable_dict(self):
        def view(request):
            return {'a':1}
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        try:
            result(None, None)
        except ValueError as e:
            self.assertEqual(
                e.args[0],
                "Could not convert return value of the view callable function "
                "pyramid.tests.test_viewderivers.view into a response "
                "object. The value returned was {'a': 1}. You may have "
                "forgotten to define a renderer in the view configuration."
                )
        else: # pragma: no cover
            raise AssertionError

    def test_instance_returns_non_adaptable(self):
        class AView(object):
            def __call__(self, request):
                return None
        view = AView()
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        try:
            result(None, None)
        except ValueError as e:
            msg = e.args[0]
            self.assertTrue(msg.startswith(
                'Could not convert return value of the view callable object '
                '<pyramid.tests.test_viewderivers.'))
            self.assertTrue(msg.endswith(
                '> into a response object. The value returned was None. You '
                'may have forgotten to return a value from the view callable.'))
        else: # pragma: no cover
            raise AssertionError

    def test_function_returns_true_Response_no_renderer(self):
        from pyramid.response import Response
        r = Response('Hello')
        def view(request):
            return r
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        response = result(None, None)
        self.assertEqual(response, r)

    def test_function_returns_true_Response_with_renderer(self):
        from pyramid.response import Response
        r = Response('Hello')
        def view(request):
            return r
        renderer = object()
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        response = result(None, None)
        self.assertEqual(response, r)

    def test_requestonly_default_method_returns_non_adaptable(self):
        request = DummyRequest()
        class AView(object):
            def __init__(self, request):
                pass
            def __call__(self):
                return None
        result = self.config.derive_view(AView)
        self.assertFalse(result is AView)
        try:
            result(None, request)
        except ValueError as e:
            self.assertEqual(
                e.args[0],
                'Could not convert return value of the view callable '
                'method __call__ of '
                'class pyramid.tests.test_viewderivers.AView into a '
                'response object. The value returned was None. You may have '
                'forgotten to return a value from the view callable.'
                )
        else: # pragma: no cover
            raise AssertionError

    def test_requestonly_nondefault_method_returns_non_adaptable(self):
        request = DummyRequest()
        class AView(object):
            def __init__(self, request):
                pass
            def theviewmethod(self):
                return None
        result = self.config.derive_view(AView, attr='theviewmethod')
        self.assertFalse(result is AView)
        try:
            result(None, request)
        except ValueError as e:
            self.assertEqual(
                e.args[0],
                'Could not convert return value of the view callable '
                'method theviewmethod of '
                'class pyramid.tests.test_viewderivers.AView into a '
                'response object. The value returned was None. You may have '
                'forgotten to return a value from the view callable.'
                )
        else: # pragma: no cover
            raise AssertionError

    def test_requestonly_function(self):
        response = DummyResponse()
        def view(request):
            return response
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(result(None, None), response)

    def test_requestonly_function_with_renderer(self):
        response = DummyResponse()
        class moo(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, 'OK')
                self.assertEqual(view_inst, view)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        def view(request):
            return 'OK'
        result = self.config.derive_view(view, renderer=moo())
        self.assertFalse(result.__wraps__ is view)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_requestonly_function_with_renderer_request_override(self):
        def moo(info):
            def inner(value, system):
                self.assertEqual(value, 'OK')
                self.assertEqual(system['request'], request)
                self.assertEqual(system['context'], context)
                return b'moo'
            return inner
        def view(request):
            return 'OK'
        self.config.add_renderer('moo', moo)
        result = self.config.derive_view(view, renderer='string')
        self.assertFalse(result is view)
        request = self._makeRequest()
        request.override_renderer = 'moo'
        context = testing.DummyResource()
        self.assertEqual(result(context, request).body, b'moo')

    def test_requestonly_function_with_renderer_request_has_view(self):
        response = DummyResponse()
        class moo(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, 'OK')
                self.assertEqual(view_inst, 'view')
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        def view(request):
            return 'OK'
        result = self.config.derive_view(view, renderer=moo())
        self.assertFalse(result.__wraps__ is view)
        request = self._makeRequest()
        request.__view__ = 'view'
        context = testing.DummyResource()
        r = result(context, request)
        self.assertEqual(r, response)
        self.assertFalse(hasattr(request, '__view__'))

    def test_class_without_attr(self):
        response = DummyResponse()
        class View(object):
            def __init__(self, request):
                pass
            def __call__(self):
                return response
        result = self.config.derive_view(View)
        request = self._makeRequest()
        self.assertEqual(result(None, request), response)
        self.assertEqual(request.__view__.__class__, View)

    def test_class_with_attr(self):
        response = DummyResponse()
        class View(object):
            def __init__(self, request):
                pass
            def another(self):
                return response
        result = self.config.derive_view(View, attr='another')
        request = self._makeRequest()
        self.assertEqual(result(None, request), response)
        self.assertEqual(request.__view__.__class__, View)

    def test_as_function_context_and_request(self):
        def view(context, request):
            return 'OK'
        result = self.config.derive_view(view)
        self.assertTrue(result.__wraps__ is view)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        self.assertEqual(view(None, None), 'OK')

    def test_as_function_requestonly(self):
        response = DummyResponse()
        def view(request):
            return response
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        self.assertEqual(result(None, None), response)

    def test_as_newstyle_class_context_and_request(self):
        response = DummyResponse()
        class view(object):
            def __init__(self, context, request):
                pass
            def __call__(self):
                return response
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        self.assertEqual(result(None, request), response)
        self.assertEqual(request.__view__.__class__, view)

    def test_as_newstyle_class_requestonly(self):
        response = DummyResponse()
        class view(object):
            def __init__(self, context, request):
                pass
            def __call__(self):
                return response
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        self.assertEqual(result(None, request), response)
        self.assertEqual(request.__view__.__class__, view)

    def test_as_oldstyle_class_context_and_request(self):
        response = DummyResponse()
        class view:
            def __init__(self, context, request):
                pass
            def __call__(self):
                return response
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        self.assertEqual(result(None, request), response)
        self.assertEqual(request.__view__.__class__, view)

    def test_as_oldstyle_class_requestonly(self):
        response = DummyResponse()
        class view:
            def __init__(self, context, request):
                pass
            def __call__(self):
                return response
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        self.assertEqual(result(None, request), response)
        self.assertEqual(request.__view__.__class__, view)

    def test_as_instance_context_and_request(self):
        response = DummyResponse()
        class View:
            def __call__(self, context, request):
                return response
        view = View()
        result = self.config.derive_view(view)
        self.assertTrue(result.__wraps__ is view)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        self.assertEqual(result(None, None), response)

    def test_as_instance_requestonly(self):
        response = DummyResponse()
        class View:
            def __call__(self, request):
                return response
        view = View()
        result = self.config.derive_view(view)
        self.assertFalse(result is view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertTrue('test_viewderivers' in result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        self.assertEqual(result(None, None), response)

    def test_with_debug_authorization_no_authpol(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        logger = self._registerLogger()
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): Allowed "
                         "(no authorization policy in use)")

    def test_with_debug_authorization_authn_policy_no_authz_policy(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(debug_authorization=True)
        from pyramid.interfaces import IAuthenticationPolicy
        policy = DummySecurityPolicy(False)
        self.config.registry.registerUtility(policy, IAuthenticationPolicy)
        logger = self._registerLogger()
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): Allowed "
                         "(no authorization policy in use)")

    def test_with_debug_authorization_authz_policy_no_authn_policy(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(debug_authorization=True)
        from pyramid.interfaces import IAuthorizationPolicy
        policy = DummySecurityPolicy(False)
        self.config.registry.registerUtility(policy, IAuthorizationPolicy)
        logger = self._registerLogger()
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): Allowed "
                         "(no authorization policy in use)")

    def test_with_debug_authorization_no_permission(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        self._registerSecurityPolicy(True)
        logger = self._registerLogger()
        result = self.config._derive_view(view)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): Allowed ("
                         "no permission registered)")

    def test_debug_auth_permission_authpol_permitted(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        logger = self._registerLogger()
        self._registerSecurityPolicy(True)
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertEqual(result.__call_permissive__.__wraps__, view)
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): True")

    def test_debug_auth_permission_authpol_permitted_no_request(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        logger = self._registerLogger()
        self._registerSecurityPolicy(True)
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertEqual(result.__call_permissive__.__wraps__, view)
        self.assertEqual(result(None, None), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url None (view name "
                         "None against context None): True")

    def test_debug_auth_permission_authpol_denied(self):
        from pyramid.httpexceptions import HTTPForbidden
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        logger = self._registerLogger()
        self._registerSecurityPolicy(False)
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertEqual(result.__call_permissive__.__wraps__, view)
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertRaises(HTTPForbidden, result, None, request)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): False")

    def test_debug_auth_permission_authpol_denied2(self):
        view = lambda *arg: 'OK'
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        self._registerLogger()
        self._registerSecurityPolicy(False)
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        permitted = result.__permitted__(None, None)
        self.assertEqual(permitted, False)

    def test_debug_auth_permission_authpol_overridden(self):
        from pyramid.security import NO_PERMISSION_REQUIRED
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = dict(
            debug_authorization=True, reload_templates=True)
        logger = self._registerLogger()
        self._registerSecurityPolicy(False)
        result = self.config._derive_view(view, permission=NO_PERMISSION_REQUIRED)
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)
        self.assertEqual(len(logger.messages), 1)
        self.assertEqual(logger.messages[0],
                         "debug_authorization of url url (view name "
                         "'view_name' against context None): "
                         "Allowed (NO_PERMISSION_REQUIRED)")

    def test_secured_view_authn_policy_no_authz_policy(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = {}
        from pyramid.interfaces import IAuthenticationPolicy
        policy = DummySecurityPolicy(False)
        self.config.registry.registerUtility(policy, IAuthenticationPolicy)
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)

    def test_secured_view_authz_policy_no_authn_policy(self):
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = {}
        from pyramid.interfaces import IAuthorizationPolicy
        policy = DummySecurityPolicy(False)
        self.config.registry.registerUtility(policy, IAuthorizationPolicy)
        result = self.config._derive_view(view, permission='view')
        self.assertEqual(view.__module__, result.__module__)
        self.assertEqual(view.__doc__, result.__doc__)
        self.assertEqual(view.__name__, result.__name__)
        self.assertFalse(hasattr(result, '__call_permissive__'))
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        self.assertEqual(result(None, request), response)

    def test_secured_view_raises_forbidden_no_name(self):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        from pyramid.httpexceptions import HTTPForbidden
        response = DummyResponse()
        view = lambda *arg: response
        self.config.registry.settings = {}
        policy = DummySecurityPolicy(False)
        self.config.registry.registerUtility(policy, IAuthenticationPolicy)
        self.config.registry.registerUtility(policy, IAuthorizationPolicy)
        result = self.config._derive_view(view, permission='view')
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        try:
            result(None, request)
        except HTTPForbidden as e:
            self.assertEqual(e.message,
                             'Unauthorized: <lambda> failed permission check')
        else: # pragma: no cover
            raise AssertionError

    def test_secured_view_raises_forbidden_with_name(self):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        from pyramid.httpexceptions import HTTPForbidden
        def myview(request): pass
        self.config.registry.settings = {}
        policy = DummySecurityPolicy(False)
        self.config.registry.registerUtility(policy, IAuthenticationPolicy)
        self.config.registry.registerUtility(policy, IAuthorizationPolicy)
        result = self.config._derive_view(myview, permission='view')
        request = self._makeRequest()
        request.view_name = 'view_name'
        request.url = 'url'
        try:
            result(None, request)
        except HTTPForbidden as e:
            self.assertEqual(e.message,
                             'Unauthorized: myview failed permission check')
        else: # pragma: no cover
            raise AssertionError

    def test_secured_view_skipped_by_default_on_exception_view(self):
        from pyramid.request import Request
        from pyramid.security import NO_PERMISSION_REQUIRED
        def view(request):
            raise ValueError
        def excview(request):
            return 'hello'
        self._registerSecurityPolicy(False)
        self.config.add_settings({'debug_authorization': True})
        self.config.set_default_permission('view')
        self.config.add_view(view, name='foo', permission=NO_PERMISSION_REQUIRED)
        self.config.add_view(excview, context=ValueError, renderer='string')
        app = self.config.make_wsgi_app()
        request = Request.blank('/foo', base_url='http://example.com')
        request.method = 'POST'
        response = request.get_response(app)
        self.assertTrue(b'hello' in response.body)

    def test_secured_view_failed_on_explicit_exception_view(self):
        from pyramid.httpexceptions import HTTPForbidden
        from pyramid.request import Request
        from pyramid.security import NO_PERMISSION_REQUIRED
        def view(request):
            raise ValueError
        def excview(request): pass
        self._registerSecurityPolicy(False)
        self.config.add_view(view, name='foo', permission=NO_PERMISSION_REQUIRED)
        self.config.add_view(excview, context=ValueError, renderer='string',
                             permission='view')
        app = self.config.make_wsgi_app()
        request = Request.blank('/foo', base_url='http://example.com')
        request.method = 'POST'
        try:
            request.get_response(app)
        except HTTPForbidden:
            pass
        else: # pragma: no cover
            raise AssertionError

    def test_secured_view_passed_on_explicit_exception_view(self):
        from pyramid.request import Request
        from pyramid.security import NO_PERMISSION_REQUIRED
        def view(request):
            raise ValueError
        def excview(request):
            return 'hello'
        self._registerSecurityPolicy(True)
        self.config.add_view(view, name='foo', permission=NO_PERMISSION_REQUIRED)
        self.config.add_view(excview, context=ValueError, renderer='string',
                             permission='view')
        app = self.config.make_wsgi_app()
        request = Request.blank('/foo', base_url='http://example.com')
        request.method = 'POST'
        request.headers['X-CSRF-Token'] = 'foo'
        response = request.get_response(app)
        self.assertTrue(b'hello' in response.body)

    def test_predicate_mismatch_view_has_no_name(self):
        from pyramid.exceptions import PredicateMismatch
        response = DummyResponse()
        view = lambda *arg: response
        def predicate1(context, request):
            return False
        predicate1.text = lambda *arg: 'text'
        result = self.config._derive_view(view, predicates=[predicate1])
        request = self._makeRequest()
        request.method = 'POST'
        try:
            result(None, None)
        except PredicateMismatch as e:
            self.assertEqual(e.detail,
                             'predicate mismatch for view <lambda> (text)')
        else: # pragma: no cover
            raise AssertionError

    def test_predicate_mismatch_view_has_name(self):
        from pyramid.exceptions import PredicateMismatch
        def myview(request): pass
        def predicate1(context, request):
            return False
        predicate1.text = lambda *arg: 'text'
        result = self.config._derive_view(myview, predicates=[predicate1])
        request = self._makeRequest()
        request.method = 'POST'
        try:
            result(None, None)
        except PredicateMismatch as e:
            self.assertEqual(e.detail,
                             'predicate mismatch for view myview (text)')
        else: # pragma: no cover
            raise AssertionError

    def test_predicate_mismatch_exception_has_text_in_detail(self):
        from pyramid.exceptions import PredicateMismatch
        def myview(request): pass
        def predicate1(context, request):
            return True
        predicate1.text = lambda *arg: 'pred1'
        def predicate2(context, request):
            return False
        predicate2.text = lambda *arg: 'pred2'
        result = self.config._derive_view(myview, 
            predicates=[predicate1, predicate2])
        request = self._makeRequest()
        request.method = 'POST'
        try:
            result(None, None)
        except PredicateMismatch as e:
            self.assertEqual(e.detail,
                             'predicate mismatch for view myview (pred2)')
        else: # pragma: no cover
            raise AssertionError

    def test_with_predicates_all(self):
        response = DummyResponse()
        view = lambda *arg: response
        predicates = []
        def predicate1(context, request):
            predicates.append(True)
            return True
        def predicate2(context, request):
            predicates.append(True)
            return True
        result = self.config._derive_view(view, 
            predicates=[predicate1, predicate2])
        request = self._makeRequest()
        request.method = 'POST'
        next = result(None, None)
        self.assertEqual(next, response)
        self.assertEqual(predicates, [True, True])

    def test_with_predicates_checker(self):
        view = lambda *arg: 'OK'
        predicates = []
        def predicate1(context, request):
            predicates.append(True)
            return True
        def predicate2(context, request):
            predicates.append(True)
            return True
        result = self.config._derive_view(view, 
            predicates=[predicate1, predicate2])
        request = self._makeRequest()
        request.method = 'POST'
        next = result.__predicated__(None, None)
        self.assertEqual(next, True)
        self.assertEqual(predicates, [True, True])

    def test_with_predicates_notall(self):
        from pyramid.httpexceptions import HTTPNotFound
        view = lambda *arg: 'OK'
        predicates = []
        def predicate1(context, request):
            predicates.append(True)
            return True
        predicate1.text = lambda *arg: 'text'
        def predicate2(context, request):
            predicates.append(True)
            return False
        predicate2.text = lambda *arg: 'text'
        result = self.config._derive_view(view, 
            predicates=[predicate1, predicate2])
        request = self._makeRequest()
        request.method = 'POST'
        self.assertRaises(HTTPNotFound, result, None, None)
        self.assertEqual(predicates, [True, True])

    def test_with_wrapper_viewname(self):
        from pyramid.response import Response
        from pyramid.interfaces import IView
        from pyramid.interfaces import IViewClassifier
        inner_response = Response('OK')
        def inner_view(context, request):
            return inner_response
        def outer_view(context, request):
            self.assertEqual(request.wrapped_response, inner_response)
            self.assertEqual(request.wrapped_body, inner_response.body)
            self.assertEqual(request.wrapped_view.__original_view__,
                             inner_view)
            return Response(b'outer ' + request.wrapped_body)
        self.config.registry.registerAdapter(
            outer_view, (IViewClassifier, None, None), IView, 'owrap')
        result = self.config._derive_view(inner_view, viewname='inner',
                                wrapper_viewname='owrap')
        self.assertFalse(result is inner_view)
        self.assertEqual(inner_view.__module__, result.__module__)
        self.assertEqual(inner_view.__doc__, result.__doc__)
        request = self._makeRequest()
        response = result(None, request)
        self.assertEqual(response.body, b'outer OK')

    def test_with_wrapper_viewname_notfound(self):
        from pyramid.response import Response
        inner_response = Response('OK')
        def inner_view(context, request):
            return inner_response
        wrapped = self.config._derive_view(inner_view, viewname='inner',
                                wrapper_viewname='owrap')
        request = self._makeRequest()
        self.assertRaises(ValueError, wrapped, None, request)

    def test_as_newstyle_class_context_and_request_attr_and_renderer(self):
        response = DummyResponse()
        class renderer(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, {'a':'1'})
                self.assertEqual(view_inst.__class__, View)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        class View(object):
            def __init__(self, context, request):
                pass
            def index(self):
                return {'a':'1'}
        result = self.config._derive_view(View, 
            renderer=renderer(), attr='index')
        self.assertFalse(result is View)
        self.assertEqual(result.__module__, View.__module__)
        self.assertEqual(result.__doc__, View.__doc__)
        self.assertEqual(result.__name__, View.__name__)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_as_newstyle_class_requestonly_attr_and_renderer(self):
        response = DummyResponse()
        class renderer(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, {'a':'1'})
                self.assertEqual(view_inst.__class__, View)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        class View(object):
            def __init__(self, request):
                pass
            def index(self):
                return {'a':'1'}
        result = self.config.derive_view(View, 
            renderer=renderer(), attr='index')
        self.assertFalse(result is View)
        self.assertEqual(result.__module__, View.__module__)
        self.assertEqual(result.__doc__, View.__doc__)
        self.assertEqual(result.__name__, View.__name__)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_as_oldstyle_cls_context_request_attr_and_renderer(self):
        response = DummyResponse()
        class renderer(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, {'a':'1'})
                self.assertEqual(view_inst.__class__, View)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        class View:
            def __init__(self, context, request):
                pass
            def index(self):
                return {'a':'1'}
        result = self.config.derive_view(View, 
            renderer=renderer(), attr='index')
        self.assertFalse(result is View)
        self.assertEqual(result.__module__, View.__module__)
        self.assertEqual(result.__doc__, View.__doc__)
        self.assertEqual(result.__name__, View.__name__)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_as_oldstyle_cls_requestonly_attr_and_renderer(self):
        response = DummyResponse()
        class renderer(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, {'a':'1'})
                self.assertEqual(view_inst.__class__, View)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        class View:
            def __init__(self, request):
                pass
            def index(self):
                return {'a':'1'}
        result = self.config.derive_view(View, 
            renderer=renderer(), attr='index')
        self.assertFalse(result is View)
        self.assertEqual(result.__module__, View.__module__)
        self.assertEqual(result.__doc__, View.__doc__)
        self.assertEqual(result.__name__, View.__name__)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_as_instance_context_and_request_attr_and_renderer(self):
        response = DummyResponse()
        class renderer(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, {'a':'1'})
                self.assertEqual(view_inst, view)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        class View:
            def index(self, context, request):
                return {'a':'1'}
        view = View()
        result = self.config.derive_view(view, 
            renderer=renderer(), attr='index')
        self.assertFalse(result is view)
        self.assertEqual(result.__module__, view.__module__)
        self.assertEqual(result.__doc__, view.__doc__)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_as_instance_requestonly_attr_and_renderer(self):
        response = DummyResponse()
        class renderer(object):
            def render_view(inself, req, resp, view_inst, ctx):
                self.assertEqual(req, request)
                self.assertEqual(resp, {'a':'1'})
                self.assertEqual(view_inst, view)
                self.assertEqual(ctx, context)
                return response
            def clone(self):
                return self
        class View:
            def index(self, request):
                return {'a':'1'}
        view = View()
        result = self.config.derive_view(view, 
            renderer=renderer(), attr='index')
        self.assertFalse(result is view)
        self.assertEqual(result.__module__, view.__module__)
        self.assertEqual(result.__doc__, view.__doc__)
        request = self._makeRequest()
        context = testing.DummyResource()
        self.assertEqual(result(context, request), response)

    def test_with_view_mapper_config_specified(self):
        response = DummyResponse()
        class mapper(object):
            def __init__(self, **kw):
                self.kw = kw
            def __call__(self, view):
                def wrapped(context, request):
                    return response
                return wrapped
        def view(context, request): return 'NOTOK'
        result = self.config._derive_view(view, mapper=mapper)
        self.assertFalse(result.__wraps__ is view)
        self.assertEqual(result(None, None), response)

    def test_with_view_mapper_view_specified(self):
        from pyramid.response import Response
        response = Response()
        def mapper(**kw):
            def inner(view):
                def superinner(context, request):
                    self.assertEqual(request, None)
                    return response
                return superinner
            return inner
        def view(context, request): return 'NOTOK'
        view.__view_mapper__ = mapper
        result = self.config.derive_view(view)
        self.assertFalse(result.__wraps__ is view)
        self.assertEqual(result(None, None), response)

    def test_with_view_mapper_default_mapper_specified(self):
        from pyramid.response import Response
        response = Response()
        def mapper(**kw):
            def inner(view):
                def superinner(context, request):
                    self.assertEqual(request, None)
                    return  response
                return superinner
            return inner
        self.config.set_view_mapper(mapper)
        def view(context, request): return 'NOTOK'
        result = self.config.derive_view(view)
        self.assertFalse(result.__wraps__ is view)
        self.assertEqual(result(None, None), response)

    def test_attr_wrapped_view_branching_default_phash(self):
        from pyramid.config.util import DEFAULT_PHASH
        def view(context, request): pass
        result = self.config._derive_view(view, phash=DEFAULT_PHASH)
        self.assertEqual(result.__wraps__, view)

    def test_attr_wrapped_view_branching_nondefault_phash(self):
        def view(context, request): pass
        result = self.config._derive_view(view, phash='nondefault')
        self.assertNotEqual(result, view)

    def test_http_cached_view_integer(self):
        import datetime
        from pyramid.response import Response
        response = Response('OK')
        def inner_view(context, request):
            return response
        result = self.config._derive_view(inner_view, http_cache=3600)
        self.assertFalse(result is inner_view)
        self.assertEqual(inner_view.__module__, result.__module__)
        self.assertEqual(inner_view.__doc__, result.__doc__)
        request = self._makeRequest()
        when = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        result = result(None, request)
        self.assertEqual(result, response)
        headers = dict(result.headerlist)
        expires = parse_httpdate(headers['Expires'])
        assert_similar_datetime(expires, when)
        self.assertEqual(headers['Cache-Control'], 'max-age=3600')

    def test_http_cached_view_timedelta(self):
        import datetime
        from pyramid.response import Response
        response = Response('OK')
        def inner_view(context, request):
            return response
        result = self.config._derive_view(inner_view, 
            http_cache=datetime.timedelta(hours=1))
        self.assertFalse(result is inner_view)
        self.assertEqual(inner_view.__module__, result.__module__)
        self.assertEqual(inner_view.__doc__, result.__doc__)
        request = self._makeRequest()
        when = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        result = result(None, request)
        self.assertEqual(result, response)
        headers = dict(result.headerlist)
        expires = parse_httpdate(headers['Expires'])
        assert_similar_datetime(expires, when)
        self.assertEqual(headers['Cache-Control'], 'max-age=3600')

    def test_http_cached_view_tuple(self):
        import datetime
        from pyramid.response import Response
        response = Response('OK')
        def inner_view(context, request):
            return response
        result = self.config._derive_view(inner_view,
            http_cache=(3600, {'public':True}))
        self.assertFalse(result is inner_view)
        self.assertEqual(inner_view.__module__, result.__module__)
        self.assertEqual(inner_view.__doc__, result.__doc__)
        request = self._makeRequest()
        when = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        result = result(None, request)
        self.assertEqual(result, response)
        headers = dict(result.headerlist)
        expires = parse_httpdate(headers['Expires'])
        assert_similar_datetime(expires, when)
        self.assertEqual(headers['Cache-Control'], 'max-age=3600, public')

    def test_http_cached_view_tuple_seconds_None(self):
        from pyramid.response import Response
        response = Response('OK')
        def inner_view(context, request):
            return response
        result = self.config._derive_view(inner_view,
            http_cache=(None, {'public':True}))
        self.assertFalse(result is inner_view)
        self.assertEqual(inner_view.__module__, result.__module__)
        self.assertEqual(inner_view.__doc__, result.__doc__)
        request = self._makeRequest()
        result = result(None, request)
        self.assertEqual(result, response)
        headers = dict(result.headerlist)
        self.assertFalse('Expires' in headers)
        self.assertEqual(headers['Cache-Control'], 'public')

    def test_http_cached_view_prevent_auto_set(self):
        from pyramid.response import Response
        response = Response()
        response.cache_control.prevent_auto = True
        def inner_view(context, request):
            return response
        result = self.config._derive_view(inner_view, http_cache=3600)
        request = self._makeRequest()
        result = result(None, request)
        self.assertEqual(result, response) # doesn't blow up
        headers = dict(result.headerlist)
        self.assertFalse('Expires' in headers)
        self.assertFalse('Cache-Control' in headers)

    def test_http_cached_prevent_http_cache_in_settings(self):
        self.config.registry.settings['prevent_http_cache'] = True
        from pyramid.response import Response
        response = Response()
        def inner_view(context, request):
            return response
        result = self.config._derive_view(inner_view, http_cache=3600)
        request = self._makeRequest()
        result = result(None, request)
        self.assertEqual(result, response)
        headers = dict(result.headerlist)
        self.assertFalse('Expires' in headers)
        self.assertFalse('Cache-Control' in headers)

    def test_http_cached_view_bad_tuple(self):
        def view(request): pass
        self.assertRaises(ConfigurationError, self.config._derive_view, 
            view, http_cache=(None,))

    def test_csrf_view_ignores_GET(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.method = 'GET'
        view = self.config._derive_view(inner_view, require_csrf=True)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_fails_with_bad_POST_header(self):
        from pyramid.exceptions import BadCSRFToken
        def inner_view(request): pass
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.headers = {'X-CSRF-Token': 'bar'}
        view = self.config._derive_view(inner_view, require_csrf=True)
        self.assertRaises(BadCSRFToken, lambda: view(None, request))

    def test_csrf_view_passes_with_good_POST_header(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.headers = {'X-CSRF-Token': 'foo'}
        view = self.config._derive_view(inner_view, require_csrf=True)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_fails_with_bad_POST_token(self):
        from pyramid.exceptions import BadCSRFToken
        def inner_view(request): pass
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.POST = {'csrf_token': 'bar'}
        view = self.config._derive_view(inner_view, require_csrf=True)
        self.assertRaises(BadCSRFToken, lambda: view(None, request))

    def test_csrf_view_passes_with_good_POST_token(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.POST = {'csrf_token': 'foo'}
        view = self.config._derive_view(inner_view, require_csrf=True)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_https_domain(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "https"
        request.domain = "example.com"
        request.host_port = "443"
        request.referrer = "https://example.com/login/"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.POST = {'csrf_token': 'foo'}
        view = self.config._derive_view(inner_view, require_csrf=True)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_fails_on_bad_PUT_header(self):
        from pyramid.exceptions import BadCSRFToken
        def inner_view(request): pass
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'PUT'
        request.session = DummySession({'csrf_token': 'foo'})
        request.headers = {'X-CSRF-Token': 'bar'}
        view = self.config._derive_view(inner_view, require_csrf=True)
        self.assertRaises(BadCSRFToken, lambda: view(None, request))

    def test_csrf_view_fails_on_bad_referrer(self):
        from pyramid.exceptions import BadCSRFOrigin
        def inner_view(request): pass
        request = self._makeRequest()
        request.method = "POST"
        request.scheme = "https"
        request.host_port = "443"
        request.domain = "example.com"
        request.referrer = "https://not-example.com/evil/"
        request.registry.settings = {}
        view = self.config._derive_view(inner_view, require_csrf=True)
        self.assertRaises(BadCSRFOrigin, lambda: view(None, request))

    def test_csrf_view_fails_on_bad_origin(self):
        from pyramid.exceptions import BadCSRFOrigin
        def inner_view(request): pass
        request = self._makeRequest()
        request.method = "POST"
        request.scheme = "https"
        request.host_port = "443"
        request.domain = "example.com"
        request.headers = {"Origin": "https://not-example.com/evil/"}
        request.registry.settings = {}
        view = self.config._derive_view(inner_view, require_csrf=True)
        self.assertRaises(BadCSRFOrigin, lambda: view(None, request))

    def test_csrf_view_enabled_by_default(self):
        from pyramid.exceptions import BadCSRFToken
        def inner_view(request): pass
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        self.config.set_default_csrf_options(require_csrf=True)
        view = self.config._derive_view(inner_view)
        self.assertRaises(BadCSRFToken, lambda: view(None, request))

    def test_csrf_view_uses_custom_csrf_token(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.POST = {'DUMMY': 'foo'}
        self.config.set_default_csrf_options(require_csrf=True, token='DUMMY')
        view = self.config._derive_view(inner_view)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_uses_custom_csrf_header(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.headers = {'DUMMY': 'foo'}
        self.config.set_default_csrf_options(require_csrf=True, header='DUMMY')
        view = self.config._derive_view(inner_view)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_uses_custom_methods(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'PUT'
        request.session = DummySession({'csrf_token': 'foo'})
        self.config.set_default_csrf_options(
            require_csrf=True, safe_methods=['PUT'])
        view = self.config._derive_view(inner_view)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_uses_view_option_override(self):
        response = DummyResponse()
        def inner_view(request):
            return response
        request = self._makeRequest()
        request.scheme = "http"
        request.method = 'POST'
        request.session = DummySession({'csrf_token': 'foo'})
        request.POST = {'csrf_token': 'bar'}
        self.config.set_default_csrf_options(require_csrf=True)
        view = self.config._derive_view(inner_view, require_csrf=False)
        result = view(None, request)
        self.assertTrue(result is response)

    def test_csrf_view_skipped_by_default_on_exception_view(self):
        from pyramid.request import Request
        def view(request):
            raise ValueError
        def excview(request):
            return 'hello'
        self.config.set_default_csrf_options(require_csrf=True)
        self.config.set_session_factory(
            lambda request: DummySession({'csrf_token': 'foo'}))
        self.config.add_view(view, name='foo', require_csrf=False)
        self.config.add_view(excview, context=ValueError, renderer='string')
        app = self.config.make_wsgi_app()
        request = Request.blank('/foo', base_url='http://example.com')
        request.method = 'POST'
        response = request.get_response(app)
        self.assertTrue(b'hello' in response.body)

    def test_csrf_view_failed_on_explicit_exception_view(self):
        from pyramid.exceptions import BadCSRFToken
        from pyramid.request import Request
        def view(request):
            raise ValueError
        def excview(request): pass
        self.config.set_default_csrf_options(require_csrf=True)
        self.config.set_session_factory(
            lambda request: DummySession({'csrf_token': 'foo'}))
        self.config.add_view(view, name='foo', require_csrf=False)
        self.config.add_view(excview, context=ValueError, renderer='string',
                             require_csrf=True)
        app = self.config.make_wsgi_app()
        request = Request.blank('/foo', base_url='http://example.com')
        request.method = 'POST'
        try:
            request.get_response(app)
        except BadCSRFToken:
            pass
        else: # pragma: no cover
            raise AssertionError

    def test_csrf_view_passed_on_explicit_exception_view(self):
        from pyramid.request import Request
        def view(request):
            raise ValueError
        def excview(request):
            return 'hello'
        self.config.set_default_csrf_options(require_csrf=True)
        self.config.set_session_factory(
            lambda request: DummySession({'csrf_token': 'foo'}))
        self.config.add_view(view, name='foo', require_csrf=False)
        self.config.add_view(excview, context=ValueError, renderer='string',
                             require_csrf=True)
        app = self.config.make_wsgi_app()
        request = Request.blank('/foo', base_url='http://example.com')
        request.method = 'POST'
        request.headers['X-CSRF-Token'] = 'foo'
        response = request.get_response(app)
        self.assertTrue(b'hello' in response.body)


class TestDerivationOrder(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        self.config = None
        testing.tearDown()

    def test_right_order_user_sorted(self):
        from pyramid.interfaces import IViewDerivers

        self.config.add_view_deriver(None, 'deriv1')
        self.config.add_view_deriver(None, 'deriv2', 'decorated_view', 'deriv1')
        self.config.add_view_deriver(None, 'deriv3', 'deriv2', 'deriv1')

        derivers = self.config.registry.getUtility(IViewDerivers)
        derivers_sorted = derivers.sorted()
        dlist = [d for (d, _) in derivers_sorted]
        self.assertEqual([
            'secured_view',
            'csrf_view',
            'owrapped_view',
            'http_cached_view',
            'decorated_view',
            'deriv2',
            'deriv3',
            'deriv1',
            'rendered_view',
            'mapped_view',
            ], dlist)

    def test_right_order_implicit(self):
        from pyramid.interfaces import IViewDerivers

        self.config.add_view_deriver(None, 'deriv1')
        self.config.add_view_deriver(None, 'deriv2')
        self.config.add_view_deriver(None, 'deriv3')

        derivers = self.config.registry.getUtility(IViewDerivers)
        derivers_sorted = derivers.sorted()
        dlist = [d for (d, _) in derivers_sorted]
        self.assertEqual([
            'secured_view',
            'csrf_view',
            'owrapped_view',
            'http_cached_view',
            'decorated_view',
            'deriv3',
            'deriv2',
            'deriv1',
            'rendered_view',
            'mapped_view',
            ], dlist)

    def test_right_order_under_rendered_view(self):
        from pyramid.interfaces import IViewDerivers

        self.config.add_view_deriver(None, 'deriv1', 'rendered_view', 'mapped_view')

        derivers = self.config.registry.getUtility(IViewDerivers)
        derivers_sorted = derivers.sorted()
        dlist = [d for (d, _) in derivers_sorted]
        self.assertEqual([
            'secured_view',
            'csrf_view',
            'owrapped_view',
            'http_cached_view',
            'decorated_view',
            'rendered_view',
            'deriv1',
            'mapped_view',
            ], dlist)


    def test_right_order_under_rendered_view_others(self):
        from pyramid.interfaces import IViewDerivers

        self.config.add_view_deriver(None, 'deriv1', 'rendered_view', 'mapped_view')
        self.config.add_view_deriver(None, 'deriv2')
        self.config.add_view_deriver(None, 'deriv3')

        derivers = self.config.registry.getUtility(IViewDerivers)
        derivers_sorted = derivers.sorted()
        dlist = [d for (d, _) in derivers_sorted]
        self.assertEqual([
            'secured_view',
            'csrf_view',
            'owrapped_view',
            'http_cached_view',
            'decorated_view',
            'deriv3',
            'deriv2',
            'rendered_view',
            'deriv1',
            'mapped_view',
            ], dlist)


class TestAddDeriver(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        self.config = None
        testing.tearDown()

    def test_add_single_deriver(self):
        response = DummyResponse()
        response.deriv = False
        view = lambda *arg: response

        def deriv(view, info):
            self.assertFalse(response.deriv)
            response.deriv = True
            return view

        result = self.config._derive_view(view)
        self.assertFalse(response.deriv)
        self.config.add_view_deriver(deriv, 'test_deriv')

        result = self.config._derive_view(view)
        self.assertTrue(response.deriv)

    def test_override_deriver(self):
        flags = {}

        class AView:
            def __init__(self):
                self.response = DummyResponse()

        def deriv1(view, info):
            flags['deriv1'] = True
            return view

        def deriv2(view, info):
            flags['deriv2'] = True
            return view

        view1 = AView()
        self.config.add_view_deriver(deriv1, 'test_deriv')
        result = self.config._derive_view(view1)
        self.assertTrue(flags.get('deriv1'))
        self.assertFalse(flags.get('deriv2'))

        flags.clear()
        view2 = AView()
        self.config.add_view_deriver(deriv2, 'test_deriv')
        result = self.config._derive_view(view2)
        self.assertFalse(flags.get('deriv1'))
        self.assertTrue(flags.get('deriv2'))

    def test_override_mapped_view(self):
        from pyramid.viewderivers import VIEW
        response = DummyResponse()
        view = lambda *arg: response
        flags = {}

        def deriv1(view, info):
            flags['deriv1'] = True
            return view

        result = self.config._derive_view(view)
        self.assertFalse(flags.get('deriv1'))

        flags.clear()
        self.config.add_view_deriver(
            deriv1, name='mapped_view', under='rendered_view', over=VIEW)
        result = self.config._derive_view(view)
        self.assertTrue(flags.get('deriv1'))

    def test_add_multi_derivers_ordered(self):
        from pyramid.viewderivers import INGRESS
        response = DummyResponse()
        view = lambda *arg: response
        response.deriv = []

        def deriv1(view, info):
            response.deriv.append('deriv1')
            return view

        def deriv2(view, info):
            response.deriv.append('deriv2')
            return view

        def deriv3(view, info):
            response.deriv.append('deriv3')
            return view

        self.config.add_view_deriver(deriv1, 'deriv1')
        self.config.add_view_deriver(deriv2, 'deriv2', INGRESS, 'deriv1')
        self.config.add_view_deriver(deriv3, 'deriv3', 'deriv2', 'deriv1')
        result = self.config._derive_view(view)
        self.assertEqual(response.deriv, ['deriv1', 'deriv3', 'deriv2'])

    def test_add_deriver_without_name(self):
        from pyramid.interfaces import IViewDerivers
        def deriv1(view, info): pass
        self.config.add_view_deriver(deriv1)
        derivers = self.config.registry.getUtility(IViewDerivers)
        self.assertTrue('deriv1' in derivers.names)

    def test_add_deriver_reserves_ingress(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.viewderivers import INGRESS
        def deriv1(view, info): pass
        self.assertRaises(
            ConfigurationError, self.config.add_view_deriver, deriv1, INGRESS)

    def test_add_deriver_enforces_ingress_is_first(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.viewderivers import INGRESS
        def deriv1(view, info): pass
        try:
            self.config.add_view_deriver(deriv1, over=INGRESS)
        except ConfigurationError as ex:
            self.assertTrue('cannot be over INGRESS' in ex.args[0])
        else: # pragma: no cover
            raise AssertionError

    def test_add_deriver_enforces_view_is_last(self):
        from pyramid.exceptions import ConfigurationError
        from pyramid.viewderivers import VIEW
        def deriv1(view, info): pass
        try:
            self.config.add_view_deriver(deriv1, under=VIEW)
        except ConfigurationError as ex:
            self.assertTrue('cannot be under VIEW' in ex.args[0])
        else: # pragma: no cover
            raise AssertionError

    def test_add_deriver_enforces_mapped_view_is_last(self):
        from pyramid.exceptions import ConfigurationError
        def deriv1(view, info): pass
        try:
            self.config.add_view_deriver(deriv1, 'deriv1', under='mapped_view')
        except ConfigurationError as ex:
            self.assertTrue('cannot be under "mapped_view"' in ex.args[0])
        else: # pragma: no cover
            raise AssertionError


class TestDeriverIntegration(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        self.config = None
        testing.tearDown()

    def _getViewCallable(self, config, ctx_iface=None, request_iface=None,
                         name=''):
        from zope.interface import Interface
        from pyramid.interfaces import IRequest
        from pyramid.interfaces import IView
        from pyramid.interfaces import IViewClassifier
        classifier = IViewClassifier
        if ctx_iface is None:
            ctx_iface = Interface
        if request_iface is None:
            request_iface = IRequest
        return config.registry.adapters.lookup(
            (classifier, request_iface, ctx_iface), IView, name=name,
            default=None)

    def _makeRequest(self, config):
        request = DummyRequest()
        request.registry = config.registry
        return request

    def test_view_options(self):
        response = DummyResponse()
        view = lambda *arg: response
        response.deriv = []

        def deriv1(view, info):
            response.deriv.append(info.options['deriv1'])
            return view
        deriv1.options = ('deriv1',)

        def deriv2(view, info):
            response.deriv.append(info.options['deriv2'])
            return view
        deriv2.options = ('deriv2',)

        self.config.add_view_deriver(deriv1, 'deriv1')
        self.config.add_view_deriver(deriv2, 'deriv2')
        self.config.add_view(view, deriv1='test1', deriv2='test2')

        wrapper = self._getViewCallable(self.config)
        request = self._makeRequest(self.config)
        request.method = 'GET'
        self.assertEqual(wrapper(None, request), response)
        self.assertEqual(['test1', 'test2'], response.deriv)

    def test_unexpected_view_options(self):
        from pyramid.exceptions import ConfigurationError
        def deriv1(view, info): pass
        self.config.add_view_deriver(deriv1, 'deriv1')
        self.assertRaises(
            ConfigurationError,
            lambda: self.config.add_view(lambda r: {}, deriv1='test1'))

@implementer(IResponse)
class DummyResponse(object):
    content_type = None
    default_content_type = None
    body = None

class DummyRequest:
    subpath = ()
    matchdict = None
    request_iface  = IRequest

    def __init__(self, environ=None):
        if environ is None:
            environ = {}
        self.environ = environ
        self.params = {}
        self.POST = {}
        self.cookies = {}
        self.headers = {}
        self.response = DummyResponse()

class DummyLogger:
    def __init__(self):
        self.messages = []
    def info(self, msg):
        self.messages.append(msg)
    warn = info
    debug = info

class DummySecurityPolicy:
    def __init__(self, permitted=True):
        self.permitted = permitted

    def effective_principals(self, request):
        return []

    def permits(self, context, principals, permission):
        return self.permitted

class DummySession(dict):
    def get_csrf_token(self):
        return self['csrf_token']

def parse_httpdate(s):
    import datetime
    # cannot use %Z, must use literal GMT; Jython honors timezone
    # but CPython does not
    return datetime.datetime.strptime(s, "%a, %d %b %Y %H:%M:%S GMT")

def assert_similar_datetime(one, two):
    for attr in ('year', 'month', 'day', 'hour', 'minute'):
        one_attr = getattr(one, attr)
        two_attr = getattr(two, attr)
        if not one_attr == two_attr: # pragma: no cover
            raise AssertionError('%r != %r in %s' % (one_attr, two_attr, attr))
