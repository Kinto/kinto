# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid import testing
from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.exceptions import NotFound, HTTPBadRequest
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.response import Response
from pyramid.view import view_config
from zope.interface import implementer

from webtest import TestApp

from cornice.service import Service
from cornice.tests.support import TestCase, CatchErrors


squirel = Service(path='/squirel', name='squirel', cors_origins=('foobar',))
spam = Service(path='/spam', name='spam', cors_origins=('*',))
eggs = Service(path='/eggs', name='egg', cors_origins=('*',),
               cors_expose_all_headers=False)
bacon = Service(path='/bacon/{type}', name='bacon', cors_origins=('*',))


class Klass(object):
    """
    Class implementation of a service
    """
    def __init__(self, request):
        self.request = request

    def post(self):
        return "moar squirels (take care)"

cors_policy = {'origins': ('*',), 'enabled': True, 'credentials': True}

cors_klass = Service(name='cors_klass',
                     path='/cors_klass',
                     klass=Klass,
                     cors_policy=cors_policy)
cors_klass.add_view('post', 'post')


@squirel.get(cors_origins=('notmyidea.org',), cors_headers=('X-My-Header',))
def get_squirel(request):
    return "squirels"


@squirel.post(cors_enabled=False, cors_headers=('X-Another-Header'))
def post_squirel(request):
    return "moar squirels (take care)"


@squirel.put()
def put_squirel(request):
    return "squirels!"


@spam.get(cors_credentials=True, cors_headers=('X-My-Header'),
          cors_max_age=42)
def gimme_some_spam_please(request):
    return 'spam'


@spam.post(permission='read-only')
def moar_spam(request):
    return 'moar spam'


def is_bacon_good(request):
    if not request.matchdict['type'].endswith('good'):
        request.errors.add('querystring', 'type', 'should be better!')


@bacon.get(validators=is_bacon_good)
def get_some_bacon(request):
    # Okay, you there. Bear in mind, the only kind of bacon existing is 'good'.
    if request.matchdict['type'] != 'good':
        raise NotFound(detail='Not. Found.')
    return "yay"


@bacon.post()
def post_some_bacon(request):
    return Response()


@bacon.put()
def put_some_bacon(request):
    raise HTTPBadRequest()


@view_config(route_name='noservice')
def noservice(request):
    return Response('No Service here.')


class TestCORS(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('cornice')
        self.config.add_route('noservice', '/noservice')
        self.config.scan('cornice.tests.test_cors')
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_preflight_cors_klass_post(self):
        resp = self.app.options('/cors_klass',
                                status=200,
                                headers={
                                    'Origin': 'lolnet.org',
                                    'Access-Control-Request-Method': 'POST'})
        self.assertEqual('POST,OPTIONS',
                         dict(resp.headers)['Access-Control-Allow-Methods'])

    def test_preflight_cors_klass_put(self):
        self.app.options('/cors_klass',
                         status=400,
                         headers={
                             'Origin': 'lolnet.org',
                             'Access-Control-Request-Method': 'PUT'})

    def test_preflight_missing_headers(self):
        # we should have an OPTION method defined.
        # If we just try to reach it, without using correct headers:
        # "Access-Control-Request-Method"or without the "Origin" header,
        # we should get a 400.
        resp = self.app.options('/squirel', status=400)
        self.assertEqual(len(resp.json['errors']), 2)

    def test_preflight_missing_origin(self):

        resp = self.app.options(
            '/squirel',
            headers={'Access-Control-Request-Method': 'GET'},
            status=400)
        self.assertEqual(len(resp.json['errors']), 1)

    def test_preflight_does_not_expose_headers(self):
        resp = self.app.options(
            '/squirel',
            headers={'Access-Control-Request-Method': 'GET',
                     'Origin': 'notmyidea.org'},
            status=200)
        self.assertNotIn('Access-Control-Expose-Headers', resp.headers)

    def test_preflight_missing_request_method(self):

        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'foobar.org'},
            status=400)

        self.assertEqual(len(resp.json['errors']), 1)

    def test_preflight_incorrect_origin(self):
        # we put "lolnet.org" where only "notmyidea.org" is authorized
        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'lolnet.org',
                     'Access-Control-Request-Method': 'GET'},
            status=400)
        self.assertEqual(len(resp.json['errors']), 1)

    def test_preflight_correct_origin(self):
        resp = self.app.options(
            '/squirel',
            headers={'Origin': 'notmyidea.org',
                     'Access-Control-Request-Method': 'GET'})
        self.assertEqual(
            resp.headers['Access-Control-Allow-Origin'],
            'notmyidea.org')

        allowed_methods = (resp.headers['Access-Control-Allow-Methods']
                           .split(','))

        self.assertNotIn('POST', allowed_methods)
        self.assertIn('GET', allowed_methods)
        self.assertIn('PUT', allowed_methods)
        self.assertIn('HEAD', allowed_methods)

        allowed_headers = (resp.headers['Access-Control-Allow-Headers']
                           .split(','))

        self.assertIn('X-My-Header', allowed_headers)
        self.assertNotIn('X-Another-Header', allowed_headers)

    def test_preflight_deactivated_method(self):
        self.app.options('/squirel',
                         headers={'Origin': 'notmyidea.org',
                                  'Access-Control-Request-Method': 'POST'},
                         status=400)

    def test_preflight_origin_not_allowed_for_method(self):
        self.app.options('/squirel',
                         headers={'Origin': 'notmyidea.org',
                                  'Access-Control-Request-Method': 'PUT'},
                         status=400)

    def test_preflight_credentials_are_supported(self):
        resp = self.app.options(
            '/spam', headers={'Origin': 'notmyidea.org',
                              'Access-Control-Request-Method': 'GET'})
        self.assertIn('Access-Control-Allow-Credentials', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                         'true')

    def test_preflight_credentials_header_not_included_when_not_needed(self):
        resp = self.app.options(
            '/spam', headers={'Origin': 'notmyidea.org',
                              'Access-Control-Request-Method': 'POST'})

        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_preflight_contains_max_age(self):
        resp = self.app.options(
            '/spam', headers={'Origin': 'notmyidea.org',
                              'Access-Control-Request-Method': 'GET'})

        self.assertIn('Access-Control-Max-Age', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Max-Age'], '42')

    def test_resp_dont_include_allow_origin(self):
        resp = self.app.get('/squirel')  # omit the Origin header
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEqual(resp.json, 'squirels')

    def test_origin_is_not_wildcard_if_allow_credentials(self):
        resp = self.app.options(
            '/cors_klass',
            status=200,
            headers={
                'Origin': 'lolnet.org',
                'Access-Control-Request-Method': 'POST',
            })
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'],
                         'lolnet.org')
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                         'true')

    def test_responses_include_an_allow_origin_header(self):
        resp = self.app.get('/squirel', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'],
                         'notmyidea.org')

    def test_credentials_are_included(self):
        resp = self.app.get('/spam', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Credentials', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                         'true')

    def test_headers_are_exposed(self):
        resp = self.app.get('/squirel', headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Expose-Headers', resp.headers)

        headers = resp.headers['Access-Control-Expose-Headers'].split(',')
        self.assertIn('X-My-Header', headers)

    def test_preflight_request_headers_are_included(self):
        resp = self.app.options(
            '/squirel', headers={
                'Origin': 'notmyidea.org',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'foo,    bar,baz  '})
        # The specification says we can have any number of LWS (Linear white
        # spaces) in the values and that it should be removed.

        # per default, they should be authorized, and returned in the list of
        # authorized headers
        headers = resp.headers['Access-Control-Allow-Headers'].split(',')
        self.assertIn('foo', headers)
        self.assertIn('bar', headers)
        self.assertIn('baz', headers)

    def test_preflight_request_headers_isnt_too_permissive(self):
        self.app.options(
            '/eggs', headers={
                'Origin': 'notmyidea.org',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'foo,bar,baz'},
            status=400)

    def test_preflight_headers_arent_case_sensitive(self):
        self.app.options('/spam', headers={
            'Origin': 'notmyidea.org',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'x-my-header', })

    def test_400_returns_CORS_headers(self):
        resp = self.app.get('/bacon/not', status=400,
                            headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_404_returns_CORS_headers(self):
        resp = self.app.get('/bacon/notgood', status=404,
                            headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_response_returns_CORS_headers(self):
        resp = self.app.post('/bacon/response', status=200,
                             headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_raise_returns_CORS_headers(self):
        resp = self.app.put('/bacon/raise', status=400,
                            headers={'Origin': 'notmyidea.org'})
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_existing_non_service_route(self):
        resp = self.app.get('/noservice', status=200,
                            headers={'Origin': 'notmyidea.org'})
        self.assertEqual(resp.body, b'No Service here.')


class TestAuthenticatedCORS(TestCase):
    def setUp(self):

        def check_cred(username, *args, **kwargs):
            return [username]

        @implementer(IAuthorizationPolicy)
        class AuthorizationPolicy(object):
            def permits(self, context, principals, permission):
                return permission in principals

        self.config = testing.setUp()
        self.config.include('cornice')
        self.config.add_route('noservice', '/noservice')
        self.config.set_authorization_policy(AuthorizationPolicy())
        self.config.set_authentication_policy(BasicAuthAuthenticationPolicy(
            check_cred))
        self.config.set_default_permission('readwrite')
        self.config.scan('cornice.tests.test_cors')
        self.app = TestApp(CatchErrors(self.config.make_wsgi_app()))

    def tearDown(self):
        testing.tearDown()

    def test_post_on_spam_should_be_forbidden(self):
        self.app.post('/spam', status=403)

    def test_preflight_does_not_need_authentication(self):
        self.app.options('/spam', status=200,
                         headers={'Origin': 'notmyidea.org',
                                  'Access-Control-Request-Method': 'POST'})
