import mock
import unittest

from fxa import errors as fxa_errors

from .support import BaseWebTest


class LoginViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/login'

    def test_login_view_persists_state_in_cookies(self):
        r = self.app.get(self.url)
        cookies = r.headers.get('Set-Cookie')
        self.assertIn('state=', cookies)

    @mock.patch('readinglist.views.oauth.uuid.uuid4')
    def test_login_view_redirects_to_authorization(self, mocked_uuid):
        mocked_uuid.return_value = mock.MagicMock(hex='1234')
        expected_redirect = (
            'https://oauth.accounts.firefox.com/v1/authorization?action=signin'
            '&client_id=&state=1234&scope=profile')

        r = self.app.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], expected_redirect)


class TokenViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/token'

    def test_fails_if_no_ongoing_session(self):
        url = '{}?state=abc&code=1234'.format(self.url)
        self.app.get(url, status=401)

    def test_fails_if_state_or_code_is_missing(self):
        headers = {'Cookie': 'state=abc'}
        for params in ['', '?state=abc', '?code=1234']:
            self.app.get(self.url + params, headers=headers, status=400)

    def test_fails_if_state_does_not_match(self):
        url = '{}?state=abc&code=1234'.format(self.url)
        headers = {'Cookie': 'state=def'}
        self.app.get(url, headers=headers, status=400)

    @mock.patch('readinglist.views.oauth.OAuthClient.trade_code')
    def tests_returns_token_traded_against_code(self, mocked_trade):
        mocked_trade.return_value = 'oauth-token'

        url = '{}?state=abc&code=1234'.format(self.url)
        headers = {'Cookie': 'state=abc'}
        r = self.app.get(url, headers=headers)
        token = r.json['token']
        self.assertEqual(token, 'oauth-token')

    @mock.patch('readinglist.views.oauth.OAuthClient.trade_code')
    def tests_return_503_if_fxa_server_behaves_badly(self, mocked_trade):
        mocked_trade.side_effect = fxa_errors.OutOfProtocolError

        url = '{}?state=abc&code=1234'.format(self.url)
        headers = {'Cookie': 'state=abc'}
        self.app.get(url, headers=headers, status=503)

    @mock.patch('readinglist.views.oauth.OAuthClient.trade_code')
    def tests_return_400_if_client_error_detected(self, mocked_trade):
        mocked_trade.side_effect = fxa_errors.ClientError

        url = '{}?state=abc&code=1234'.format(self.url)
        headers = {'Cookie': 'state=abc'}
        self.app.get(url, headers=headers, status=400)
