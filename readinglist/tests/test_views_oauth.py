import mock
from fxa import errors as fxa_errors
from six.moves.urllib.parse import parse_qs, urlparse

from .support import BaseWebTest, unittest


class LoginViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/login?redirect=http://perdu.com/'

    def test_login_view_persists_state(self):
        r = self.app.get(self.url)
        url = r.headers['Location']
        url_fragments = urlparse(url)
        queryparams = parse_qs(url_fragments.query)
        state = queryparams['state'][0]
        self.assertEqual(self.app.app.registry.session.get(state),
                         'http://perdu.com/')

    @mock.patch('readinglist.views.oauth.uuid.uuid4')
    def test_login_view_redirects_to_authorization(self, mocked_uuid):
        mocked_uuid.return_value = mock.MagicMock(hex='1234')
        settings = self.app.app.registry.settings
        oauth_endpoint = settings.get('fxa-oauth.oauth_uri')
        client_id = settings.get('fxa-oauth.client_id')
        scope = settings.get('fxa-oauth.scope')
        expected_redirect = (
            '%s/authorization?action=signin'
            '&client_id=%s&state=1234&scope=%s' % (oauth_endpoint,
                                                   client_id, scope))

        r = self.app.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], expected_redirect)


class TokenViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/token'

    def test_fails_if_no_ongoing_session(self):
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=401)

    def test_fails_if_state_or_code_is_missing(self):
        headers = {'Cookie': 'state=abc'}
        for params in ['', '?state=abc', '?code=1234']:
            self.app.get(self.url + params, headers=headers, status=400)

    def test_fails_if_state_does_not_match(self):
        self.app.app.registry.session.set('def', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=401)

    @mock.patch('readinglist.views.oauth.OAuthClient.trade_code')
    def tests_redirects_with_token_traded_against_code(self, mocked_trade):
        mocked_trade.return_value = 'oauth-token'
        self.app.app.registry.session.set('abc', 'http://foobar?token=')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        r = self.app.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'],
                         'http://foobar?token=oauth-token')

    @mock.patch('readinglist.views.oauth.OAuthClient.trade_code')
    def tests_return_503_if_fxa_server_behaves_badly(self, mocked_trade):
        mocked_trade.side_effect = fxa_errors.OutOfProtocolError

        self.app.app.registry.session.set('abc', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=503)

    @mock.patch('readinglist.views.oauth.OAuthClient.trade_code')
    def tests_return_400_if_client_error_detected(self, mocked_trade):
        mocked_trade.side_effect = fxa_errors.ClientError

        self.app.app.registry.session.set('abc', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=400)
