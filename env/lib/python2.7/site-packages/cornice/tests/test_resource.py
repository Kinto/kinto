# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from pyramid import testing
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow
from pyramid.httpexceptions import (
    HTTPOk, HTTPForbidden
)
from webtest import TestApp
import mock

from cornice.resource import resource
from cornice.resource import view
from cornice.schemas import CorniceSchema
from cornice.tests import validationapp
from cornice.tests.support import TestCase, CatchErrors
from cornice.tests.support import dummy_factory


USERS = {1: {'name': 'gawel'}, 2: {'name': 'tarek'}}


def my_collection_acl(request):
    return [(Allow, 'alice', 'read')]


@resource(collection_path='/thing', path='/thing/{id}',
          name='thing_service', collection_acl=my_collection_acl)
class Thing(object):

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    @view(permission='read')
    def collection_get(self):
        return 'yay'


@resource(collection_path='/users', path='/users/{id}',
          name='user_service', factory=dummy_factory)
class User(object):

    def __init__(self, request, context=None):
        self.request = request
        self.context = context

    def collection_get(self):
        return {'users': list(USERS.keys())}

    @view(renderer='jsonp')
    @view(renderer='json')
    def get(self):
        return USERS.get(int(self.request.matchdict['id']))

    @view(renderer='json', accept='text/json')
    def collection_post(self):
        return {'test': 'yeah'}

    def patch(self):
        return {'test': 'yeah'}

    def collection_patch(self):
        return {'test': 'yeah'}

    def put(self):
        return dict(type=repr(self.context))


class TestResourceWarning(TestCase):
    @mock.patch('warnings.warn')
    def test_path_clash(self, mocked_warn):
        @resource(collection_path='/badthing/{id}', path='/badthing/{id}',
                  name='bad_thing_service')
        class BadThing(object):
            def __init__(self, request, context=None):
                pass

        msg = "Warning: collection_path and path are not distinct."
        mocked_warn.assert_called_with(msg)


class TestResource(TestCase):

    def setUp(self):
        from pyramid.renderers import JSONP

        self.config = testing.setUp()
        self.config.add_renderer('jsonp', JSONP(param_name='callback'))
        self.config.include("cornice")
        self.authz_policy = ACLAuthorizationPolicy()
        self.config.set_authorization_policy(self.authz_policy)

        self.authn_policy = AuthTktAuthenticationPolicy('$3kr1t')
        self.config.set_authentication_policy(self.authn_policy)
        self.config.scan("cornice.tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_basic_resource(self):
        self.assertEqual(self.app.get("/users").json, {'users': [1, 2]})

        self.assertEqual(self.app.get("/users/1").json, {'name': 'gawel'})

        resp = self.app.get("/users/1?callback=test")

        self.assertIn(b'test({"name": "gawel"})', resp.body, msg=resp.body)

    def test_accept_headers(self):
        # the accept headers should work even in case they're specified in a
        # resource method
        self.assertEqual(
            self.app.post("/users", headers={'Accept': 'text/json'},
                          params=json.dumps({'test': 'yeah'})).json,
            {'test': 'yeah'})

    def patch(self, *args, **kwargs):
        return self.app._gen_request('PATCH', *args, **kwargs)

    def test_head_and_patch(self):
        self.app.head("/users")
        self.app.head("/users/1")

        self.assertEqual(
            self.patch("/users").json,
            {'test': 'yeah'})

        self.assertEqual(
            self.patch("/users/1").json,
            {'test': 'yeah'})

    def test_context_factory(self):
        self.assertEqual(self.app.put('/users/1').json, {'type': 'context!'})

    def test_explicit_collection_service_name(self):
        route_url = testing.DummyRequest().route_url
        # service must exist
        self.assert_(route_url('collection_user_service'))

    def test_explicit_service_name(self):
        route_url = testing.DummyRequest().route_url
        self.assert_(route_url('user_service', id=42))  # service must exist

    def test_acl_support_unauthenticated_thing_get(self):
        # calling a view with permissions without an auth'd user => 403
        self.app.get('/thing', status=HTTPForbidden.code)

    def test_acl_support_authenticated_allowed_thing_get(self):
        with mock.patch.object(self.authn_policy, 'unauthenticated_userid',
                               return_value='alice'):
            result = self.app.get('/thing', status=HTTPOk.code)
            self.assertEqual("yay", result.json)

    if validationapp.COLANDER:
        def test_schema_on_resource(self):
            User.schema = CorniceSchema.from_colander(
                validationapp.FooBarSchema)
            result = self.patch("/users/1", status=400).json
            self.assertEquals(
                [(e['name'], e['description']) for e in result['errors']], [
                    ('foo', 'foo is missing'),
                    ('bar', 'bar is missing'),
                    ('yeah', 'yeah is missing'),
                ])


class NonAutocommittingConfigurationTestResource(TestCase):
    """
    Test that we don't fail Pyramid's conflict detection when using a manually-
    committing :class:`pyramid.config.Configurator` instance.
    """

    def setUp(self):
        from pyramid.renderers import JSONP
        self.config = testing.setUp(autocommit=False)
        self.config.add_renderer('jsonp', JSONP(param_name='callback'))
        self.config.include("cornice")
        self.config.scan("cornice.tests.test_resource")
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_get(self):
        self.app.get('/users/1')
