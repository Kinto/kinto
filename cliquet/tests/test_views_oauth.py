import mock
from fxa import errors as fxa_errors
from six.moves.urllib.parse import parse_qs, urlparse
from time import sleep

from .support import BaseWebTest, unittest


class DeactivatedOAuthRelierTest(BaseWebTest, unittest.TestCase):
    def get_app_settings(self):
        settings = super(DeactivatedOAuthRelierTest, self).get_app_settings()
        settings['fxa-oauth.relier.enabled'] = False
        return settings

    def test_login_view_is_not_available(self):
        self.app.get('/fxa-oauth/login', status=404)

    def test_params_view_is_still_available(self):
        self.app.get('/fxa-oauth/params', status=200)

    def test_token_view_is_not_available(self):
        self.app.get('/fxa-oauth/token', status=404)


class LoginViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/login?redirect=https://readinglist.firefox.com'

    def test_redirect_parameter_is_mandatory(self):
        url = '/fxa-oauth/login'
        r = self.app.get(url, status=400)
        self.assertIn('redirect', r.json['message'])

    def test_redirect_parameter_should_be_refused_if_not_whitelisted(self):
        url = '/fxa-oauth/login?redirect=http://not-whitelisted.tld'
        r = self.app.get(url, status=400)
        self.assertIn('redirect', r.json['message'])

    def test_redirect_parameter_should_be_accepted_if_whitelisted(self):
        with mock.patch.dict(self.app.app.registry.settings,
                             [('fxa-oauth.webapp.authorized_domains',
                               '*.whitelist.ed')]):
            url = '/fxa-oauth/login?redirect=http://iam.whitelist.ed'
            self.app.get(url)

    def test_redirect_parameter_should_be_rejected_if_no_whitelist(self):
        with mock.patch.dict(self.app.app.registry.settings,
                             [('fxa-oauth.webapp.authorized_domains',
                               '')]):
            url = '/fxa-oauth/login?redirect=http://iam.whitelist.ed'
            r = self.app.get(url, status=400)
        self.assertIn('redirect', r.json['message'])

    def test_login_view_persists_state(self):
        r = self.app.get(self.url)
        url = r.headers['Location']
        url_fragments = urlparse(url)
        queryparams = parse_qs(url_fragments.query)
        state = queryparams['state'][0]
        self.assertEqual(self.app.app.registry.cache.get(state),
                         'https://readinglist.firefox.com')

    def test_login_view_persists_state_with_expiration(self):
        r = self.app.get(self.url)
        url = r.headers['Location']
        url_fragments = urlparse(url)
        queryparams = parse_qs(url_fragments.query)
        state = queryparams['state'][0]
        self.assertEqual(self.app.app.registry.cache.ttl(state), 300)

    def test_login_view_persists_state_with_expiration_from_settings(self):
        r = self.app.get(self.url)
        url = r.headers['Location']
        url_fragments = urlparse(url)
        queryparams = parse_qs(url_fragments.query)
        state = queryparams['state'][0]
        self.assertEqual(self.app.app.registry.cache.ttl(state), 300)

    @mock.patch('cliquet.views.oauth.relier.uuid.uuid4')
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


class ParamsViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/params'

    def test_params_view_give_back_needed_values(self):
        settings = self.app.app.registry.settings
        oauth_endpoint = settings.get('fxa-oauth.oauth_uri')
        client_id = settings.get('fxa-oauth.client_id')
        scope = settings.get('fxa-oauth.scope')
        expected_body = {
            "client_id": client_id,
            "oauth_uri": oauth_endpoint,
            "scope": scope
        }

        r = self.app.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json, expected_body)


class TokenViewTest(BaseWebTest, unittest.TestCase):
    url = '/fxa-oauth/token'
    login_url = '/fxa-oauth/login?redirect=https://readinglist.firefox.com'

    def test_fails_if_no_ongoing_session(self):
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=401)

    def test_fails_if_state_or_code_is_missing(self):
        headers = {'Cookie': 'state=abc'}
        for params in ['', '?state=abc', '?code=1234']:
            r = self.app.get(self.url + params, headers=headers, status=400)
            self.assertIn('missing', r.json['message'])

    def test_fails_if_state_does_not_match(self):
        self.app.app.registry.cache.set('def', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=401)

    @mock.patch('cliquet.views.oauth.relier.OAuthClient.trade_code')
    def test_fails_if_state_was_already_consumed(self, mocked_trade):
        mocked_trade.return_value = 'oauth-token'
        self.app.app.registry.cache.set('abc', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url)
        self.app.get(url, status=401)

    @mock.patch('cliquet.views.oauth.relier.OAuthClient.trade_code')
    def test_fails_if_state_has_expired(self, mocked_trade):
        mocked_trade.return_value = 'oauth-token'
        with mock.patch.dict(self.app.app.registry.settings,
                             [('fxa-oauth.cache_ttl_seconds', 1)]):
            r = self.app.get(self.login_url)
        url = r.headers['Location']
        url_fragments = urlparse(url)
        queryparams = parse_qs(url_fragments.query)
        state = queryparams['state'][0]
        url = '{url}?state={state}&code=1234'.format(state=state, url=self.url)
        sleep(1)
        self.app.get(url, status=401)

    @mock.patch('cliquet.views.oauth.relier.OAuthClient.trade_code')
    def tests_redirects_with_token_traded_against_code(self, mocked_trade):
        mocked_trade.return_value = 'oauth-token'
        self.app.app.registry.cache.set('abc', 'http://foobar?token=')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        r = self.app.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'],
                         'http://foobar?token=oauth-token')

    @mock.patch('cliquet.views.oauth.relier.OAuthClient.trade_code')
    def tests_return_503_if_fxa_server_behaves_badly(self, mocked_trade):
        mocked_trade.side_effect = fxa_errors.OutOfProtocolError

        self.app.app.registry.cache.set('abc', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=503)

    @mock.patch('cliquet.views.oauth.relier.OAuthClient.trade_code')
    def tests_return_400_if_client_error_detected(self, mocked_trade):
        mocked_trade.side_effect = fxa_errors.ClientError

        self.app.app.registry.cache.set('abc', 'http://foobar')
        url = '{url}?state=abc&code=1234'.format(url=self.url)
        self.app.get(url, status=400)
