# flake8: noqa
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
import mock
from pyramid.interfaces import IDebugLogger
from cornice.tests.support import TestCase

from pyramid import testing
from pyramid.httpexceptions import (
    HTTPOk, HTTPForbidden, HTTPNotFound, HTTPMethodNotAllowed
)
from pyramid.response import Response
from pyramid.security import Allow, Deny, NO_PERMISSION_REQUIRED
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

import colander

from webtest import TestApp

from cornice import Service
from cornice.tests.support import CatchErrors
from cornice.tests.support import dummy_factory

from cornice.pyramidhook import register_service_views
from cornice.util import func_name

from mock import MagicMock

def my_acl(request):
    return [(Allow, 'alice', 'read'),
            (Allow, 'bob', 'write'),
            (Deny, 'carol', 'write'),
            (Allow, 'dan', ('write', 'update')),
        ]

service = Service(name="service", path="/service", acl=my_acl)


@service.get()
def return_404(request):
    raise HTTPNotFound()

@service.put(permission='update')
def update_view(request):
    return "updated_view"


@service.delete(permission='write')
def return_yay(request):
    return "yay"


class TemperatureCooler(object):
    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def get_fresh_air(self):
        resp = Response()
        resp.text = u'air with ' + repr(self.context)
        return resp

    def make_it_fresh(self, response):
        response.text = u'fresh ' + response.text
        return response

    def check_temperature(self, request):
        if not 'X-Temperature' in request.headers:
            request.errors.add('header', 'X-Temperature')

tc = Service(name="TemperatureCooler", path="/fresh-air",
             klass=TemperatureCooler, factory=dummy_factory)
tc.add_view("GET", "get_fresh_air", filters=('make_it_fresh',),
            validators=('check_temperature',))


class TestService(TestCase):

    def setUp(self):
        self.config = testing.setUp(
            settings={'pyramid.debug_authorization': True})

        # Set up debug_authorization logging to console
        logging.basicConfig(level=logging.DEBUG)
        debug_logger = logging.getLogger()
        self.config.registry.registerUtility(debug_logger, IDebugLogger)

        self.config.include("cornice")

        self.authz_policy = ACLAuthorizationPolicy()
        self.config.set_authorization_policy(self.authz_policy)

        self.authn_policy = AuthTktAuthenticationPolicy('$3kr1t')
        self.config.set_authentication_policy(self.authn_policy)

        self.config.scan("cornice.tests.test_service")
        self.config.scan("cornice.tests.test_pyramidhook")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))
        register_service_views(self.config, service)

    def tearDown(self):
        testing.tearDown()

    def test_404(self):
        # a get on a resource that explicitly return a 404 should return 404
        self.app.get("/service", status=HTTPNotFound.code)

    def test_405(self):
        # calling a unknown verb on an existing resource should return a 405
        self.app.post("/service", status=HTTPMethodNotAllowed.code)

    def test_acl_support_unauthenticated_service_delete(self):
        # calling a view with permissions without an auth'd user => 403
        self.app.delete('/service', status=HTTPForbidden.code)

    def test_acl_support_authenticated_allowed_service_delete(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid',
                               return_value='bob'):
            result = self.app.delete('/service', status=HTTPOk.code)
            self.assertEqual("yay", result.json)
        # The other user with 'write' permission
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid',
                               return_value='dan'):
            result = self.app.delete('/service', status=HTTPOk.code)
            self.assertEqual("yay", result.json)

    def test_acl_support_authenticated_valid_user_wrong_permission_service_delete(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='alice'):
            self.app.delete('/service', status=HTTPForbidden.code)

    def test_acl_support_authenticated_valid_user_permission_denied_service_delete(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='carol'):
            self.app.delete('/service', status=HTTPForbidden.code)

    def test_acl_support_authenticated_invalid_user_service_delete(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='mallory'):
            self.app.delete('/service', status=HTTPForbidden.code)

    def test_acl_support_authenticated_allowed_service_put(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='dan'):
            result = self.app.put('/service', status=HTTPOk.code)
            self.assertEqual("updated_view", result.json)

    def test_acl_support_authenticated_valid_user_wrong_permission_service_put(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='bob'):
            self.app.put('/service', status=HTTPForbidden.code)

    def test_acl_support_authenticated_valid_user_permission_denied_service_put(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='carol'):
            self.app.put('/service', status=HTTPForbidden.code)

    def test_acl_support_authenticated_invalid_user_service_put(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid', return_value='mallory'):
            self.app.put('/service', status=HTTPForbidden.code)

    def test_class_support(self):
        self.app.get('/fresh-air', status=400)
        resp = self.app.get('/fresh-air', headers={'X-Temperature': '50'})
        self.assertEqual(resp.body, b'fresh air with context!')


class WrapperService(Service):
    def get_view_wrapper(self, kw):
        def upper_wrapper(func):
            def upperizer(*args, **kwargs):
                result = func(*args, **kwargs)
                return result.upper()
            return upperizer
        return upper_wrapper


wrapper_service = WrapperService(name='wrapperservice', path='/wrapperservice')


@wrapper_service.get()
def return_foo(request):
    return 'foo'


class TestServiceWithWrapper(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_pyramidhook")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_wrapped(self):
        result = self.app.get('/wrapperservice')
        self.assertEqual(result.json, 'FOO')

    def test_func_name_undecorated_function(self):
        self.assertEqual("my_acl", func_name(my_acl))

    def test_func_name_decorated_function(self):
        self.assertEqual("return_foo", func_name(return_foo))

    def test_func_name_string(self):
        self.assertEqual("some_string", func_name("some_string"))

    def test_func_name_class_method(self):
        self.assertEqual("TestServiceWithWrapper.test_wrapped", func_name(TestServiceWithWrapper.test_wrapped))


test_service = Service(name="jardinet", path="/jardinet", traverse="/jardinet")
test_service.add_view('GET', lambda _:_)


class TestRouteWithTraverse(TestCase):

    def test_route_construction(self):
        config = MagicMock()
        config.add_route = MagicMock()

        register_service_views(config, test_service)
        self.assertTrue(
                ('traverse', '/jardinet'),
                config.add_route.called_args,
            )

    def test_route_with_prefix(self):
        config = testing.setUp(settings={})
        config.add_route = MagicMock()
        config.route_prefix = '/prefix'
        config.registry.cornice_services = {}
        config.add_directive('add_cornice_service', register_service_views)
        config.scan("cornice.tests.test_pyramidhook")

        services = config.registry.cornice_services
        self.assertTrue('/prefix/wrapperservice' in services)


class NonpickableSchema(colander.Schema):
    # Compiled regexs are, apparently, non-pickleable
    s = colander.SchemaNode(colander.String(), validator=colander.Regex('.'))


class TestServiceWithNonpickleableSchema(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.registry.cornice_services = {}

    def tearDown(self):
        testing.tearDown()

    def test(self):
        service = Service(name="test", path="/", schema=NonpickableSchema())
        service.add_view('GET', lambda _:_)
        register_service_views(self.config, service)



class TestFallbackRegistration(TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.registry.cornice_services = {}

    def tearDown(self):
        testing.tearDown()

    def test_fallback_permission(self):
        """
        Fallback view should be registered with NO_PERMISSION_REQUIRED
        Fixes: https://github.com/mozilla-services/cornice/issues/245
        """
        service = Service(name='fallback-test', path='/')
        service.add_view('GET', lambda _:_)
        register_service_views(self.config, service)

        # This is a bit baroque
        introspector = self.config.introspector
        views = introspector.get_category('views')
        fallback_views = [i for i in views
                          if i['introspectable']['route_name']=='fallback-test']

        for v in fallback_views:
            if v['introspectable'].title == u'function cornice.pyramidhook._fallback_view':
                permissions = [p['value'] for p in v['related'] if p.type_name == 'permission']
                self.assertIn(NO_PERMISSION_REQUIRED, permissions)
