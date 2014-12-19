import json
from unittest import TestCase

import mock
import responses
from requests import exceptions as requests_exceptions

from readinglist import fxa


class TradeCodeTest(TestCase):
    @responses.activate
    def setUp(self):
        responses.add(responses.POST, 'https://server/token',
            body='{"access_token": "yeah"}',
            content_type='application/json')

        self.token = fxa.trade_code(oauth_uri='https://server',
                                    client_id='abc',
                                    client_secret='cake',
                                    code='1234')

        self.resp_call = responses.calls[0]

    def test_reaches_server_on_token_url(self):
        self.assertEqual(self.resp_call.request.url,
                         'https://server/token')

    def test_posts_code_to_server(self):
        data = json.loads(self.resp_call.request.body)
        expected = {
            "client_secret": "cake",
            "code": "1234",
            "client_id": "abc"
        }
        self.assertDictEqual(data, expected)

    def test_returns_access_token_given_by_server(self):
        self.assertEqual(self.token, "yeah")


class TradeCodeErrorTest(TestCase):
    @mock.patch('readinglist.fxa.requests.post')
    def test_raises_error_if_server_is_unreachable(self, mocked_post):
        mocked_post.side_effect = requests_exceptions.RequestException

        with self.assertRaises(fxa.OAuth2Error):
            fxa.trade_code(oauth_uri='https://unknown',
                           client_id='abc',
                           client_secret='cake',
                           code='1234')

    @responses.activate
    def test_raises_error_if_response_returns_400(self):
        responses.add(responses.POST, 'https://server/token',
            body='{"errorno": "999"}', status=400,
            content_type='application/json')
        with self.assertRaises(fxa.OAuth2Error):
            fxa.trade_code(oauth_uri='https://server',
                           client_id='abc',
                           client_secret='cake',
                           code='1234')

    @responses.activate
    def test_raises_error_if_access_token_not_returned(self):
        responses.add(responses.POST, 'https://server/token',
            body='{"foo": "bar"}',
            content_type='application/json')
        with self.assertRaises(fxa.OAuth2Error):
            fxa.trade_code(oauth_uri='https://server',
                           client_id='abc',
                           client_secret='cake',
                           code='1234')


class VerifyTokenTest(TestCase):
    @responses.activate
    def setUp(self):
        responses.add(responses.POST, 'https://server/verify',
            body='{"user": "alice", "scopes": "profile", "client_id": "abc"}',
            content_type='application/json')

        self.verification = fxa.verify_token(oauth_uri='https://server',
                                             token='abc')

        self.resp_call = responses.calls[0]

    def test_reaches_server_on_verify_url(self):
        self.assertEqual(self.resp_call.request.url,
                         'https://server/verify')

    def test_posts_token_to_server(self):
        data = json.loads(self.resp_call.request.body)
        expected = {
            "token": "abc",
        }
        self.assertDictEqual(data, expected)

    def test_returns_response_given_by_server(self):
        expected = {
            "user": "alice",
            "scopes": "profile",
            "client_id": "abc"
        }
        self.assertDictEqual(self.verification, expected)


class VerifyTokenErrorTest(TestCase):
    @mock.patch('readinglist.fxa.requests.post')
    def test_raises_error_if_server_is_unreachable(self, mocked_post):
        mocked_post.side_effect = requests_exceptions.RequestException

        with self.assertRaises(fxa.OAuth2Error):
            fxa.verify_token(oauth_uri='https://unknown',
                             token='1234')

    @responses.activate
    def test_raises_error_if_response_returns_400(self):
        responses.add(responses.POST, 'https://server/verify',
            body='{"errorno": "999"}', status=400,
            content_type='application/json')
        with self.assertRaises(fxa.OAuth2Error):
            fxa.verify_token(oauth_uri='https://server',
                             token='1234')

    @responses.activate
    def test_raises_error_if_some_attributes_are_not_returned(self):
        responses.add(responses.POST, 'https://server/verify',
            body='{"foo": "bar"}',
            content_type='application/json')
        with self.assertRaises(fxa.OAuth2Error):
            fxa.verify_token(oauth_uri='https://server',
                             token='1234')


"""

Views tests

"""

from flask.ext.webtest import TestApp
from readinglist.run import app


class TestBase(object):
    def setUp(self):
        self.app = app
        self.app.config['SECRET_KEY'] = 'secret-key-for-sessions'
        self.w = TestApp(self.app, db=app.data.driver, use_session_scopes=True)


class LoginViewTest(TestBase, TestCase):
    url = '/v1/fxa-oauth/login'

    def test_login_view_persists_state_in_session(self):
        r = self.w.get(self.url)
        self.assertIsNotNone(r.session.get('state'))

    @mock.patch('readinglist.fxa.views.uuid.uuid4')
    def test_login_view_redirects_to_authorization(self, mocked_uuid):
        mocked_uuid.return_value = mock.MagicMock(hex='1234')
        expected_redirect = (
            'https://oauth.accounts.firefox.com/v1/authorization?action=signin'
            '&client_id=&state=1234&scope=profile')

        r = self.w.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], expected_redirect)


class ParamsViewTest(TestBase, TestCase):
    url = '/v1/fxa-oauth/params'

    def test_login_view_persists_state_in_session(self):
        r = self.w.get(self.url)
        self.assertIsNotNone(r.session.get('state'))

    def test_provide_oauth_parameters_and_state(self):
        r = self.w.get(self.url)
        self.assertEqual(sorted(r.json.keys()),
            ['client_id', 'oauth_uri', 'profile_uri', 'redirect_uri',
             'scope', 'state'])


class TokenViewTest(TestBase, TestCase):
    url = '/v1/fxa-oauth/token'

    def test_fails_if_no_ongoing_session(self):
        self.w.get(self.url, status=401)

    def test_fails_if_state_or_code_is_missing(self):
        with app.test_client() as c:
            for params in ['', '?state=abc', '?code=1234']:
                with c.session_transaction() as sess:
                    sess['state'] = 'abc'
                r = c.get(self.url + params)
                self.assertEqual(r.status_code, 400)

    def test_fails_if_state_does_not_match(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['state'] = 'abc'
            r = c.get(self.url + '?state=def&code=1234')
            self.assertEqual(r.status_code, 400)

    @mock.patch('readinglist.fxa.views.trade_code')
    def tests_returns_token_traded_against_code(self, mocked_trade):
        mocked_trade.return_value = 'oauth-token'

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['state'] = 'abc'
            r = c.get(self.url + '?state=abc&code=1234')

            self.assertEqual(r.status_code, 200)
            token = json.loads(r.data)['token']
            self.assertEqual(token, 'oauth-token')
