import unittest
import mock

from kinto.core.testing import DummyRequest
from kinto.plugins.openid import OpenIDConnectPolicy
from kinto.plugins.openid.utils import fetch_openid_config

from .. import support


class OpenIDWebTest(support.BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['includes'] = 'kinto.plugins.openid'
        settings['oidc.issuer_url'] = 'https://auth.mozilla.auth0.com'
        settings['oidc.client_id'] = 'abc'
        settings["oidc.client_secret"] = 'xyz'
        return settings


class HelloViewTest(OpenIDWebTest):

    def test_openid_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        assert 'openid' in capabilities
        assert 'userinfo_endpoint' in capabilities['openid']
        assert 'auth_uri' in capabilities['openid']

    def test_openid_in_openapi(self):
        resp = self.app.get('/__api__')
        assert 'openid' in resp.json['securityDefinitions']
        auth = resp.json['securityDefinitions']['openid']['authorizationUrl']
        assert auth == 'https://auth.mozilla.auth0.com/authorize'


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = OpenIDConnectPolicy()
        self.request = DummyRequest()
        self.request.registry.settings["oidc.issuer_url"] = 'https://idp'
        self.request.registry.settings["oidc.client_id"] = 'abc'

        self.request.registry.cache.get.return_value = None

        mocked = mock.patch.object(self.policy, '_verify_token')
        self.verify = mocked.start()
        self.addCleanup(mocked.stop)
        self.verify.return_value = {'sub': 'userid'}

    def test_returns_none_if_no_authorization(self):
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_returns_header_type_in_forget(self):
        h = self.policy.forget(self.request)
        assert 'bearer ' in h[0][1]

    def test_header_type_can_be_configured(self):
        self.request.registry.settings["oidc.header_type"] = 'bearer+oidc'
        h = self.policy.forget(self.request)
        assert 'bearer+oidc ' in h[0][1]

    def test_returns_none_if_no_authorization_prefix(self):
        self.request.headers['Authorization'] = 'avrbnnbrbr'
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_returns_none_if_bad_prefix(self):
        self.request.headers['Authorization'] = 'Basic avrbnnbrbr'
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_can_specify_both_id_and_access_token(self):
        self.request.headers['Authorization'] = 'Bearer id_token=jwt, access_token=bearer'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        self.verify.assert_called_with('https://idp', 'abc', 'jwt', 'bearer')

    def test_can_specify_jwt_token(self):
        self.request.headers['Authorization'] = 'Bearer j.w.t'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        self.verify.assert_called_with('https://idp', 'abc', 'j.w.t', None)

    def test_can_specify_only_opaque_access_token(self):
        self.request.headers['Authorization'] = 'Bearer xyz'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        self.verify.assert_called_with('https://idp', 'abc', None, 'xyz')

    def test_returns_none_if_no_cache_and_invalid_access_token(self):
        self.request.headers['Authorization'] = 'Bearer xyz'
        self.request.registry.cache.get.return_value = None
        self.verify.return_value = None
        assert self.policy.unauthenticated_userid(self.request) is None
        assert not self.request.registry.cache.set.called

    def test_payload_is_read_from_cache(self):
        self.request.headers['Authorization'] = 'Bearer xyz'
        self.request.registry.cache.get.return_value = {'sub': 'me'}
        self.policy.unauthenticated_userid(self.request) == 'me'

    def test_payload_is_stored_in_cache(self):
        self.request.headers['Authorization'] = 'Bearer xyz'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        assert self.request.registry.cache.set.called


class VerifyTokenTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # Populate OpenID config cache.
        with mock.patch('kinto.plugins.openid.utils.requests.get') as m:
            m.return_value.json.return_value = {'userinfo_endpoint': 'http://uinfo',
                                                'jwks_uri': 'https://jwks'}
            fetch_openid_config('https://idp')

    def setUp(self):
        self.policy = OpenIDConnectPolicy()

        mocked = mock.patch('kinto.plugins.openid.requests.get')
        self.mocked_get = mocked.start()
        self.addCleanup(mocked.stop)

        mocked = mock.patch('kinto.plugins.openid.jwt')
        self.mocked_jwt = mocked.start()
        self.addCleanup(mocked.stop)

        self.verify_kw = dict(issuer='https://idp', audience='abc')

    def test_fetches_userinfo_if_id_token_is_none(self):
        self.mocked_get.return_value.json.side_effect = [
            {"sub": "me"},
        ]
        payload = self.policy._verify_token(id_token=None, access_token='abc', **self.verify_kw)
        assert payload["sub"] == "me"

    def test_returns_none_if_fetching_userinfo_fails(self):
        self.mocked_get.return_value.raise_for_status.side_effect = ValueError
        payload = self.policy._verify_token(id_token=None, access_token='abc', **self.verify_kw)
        assert payload is None

    def test_verifies_jwt_headers(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": []},
        ]
        self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        self.mocked_jwt.get_unverified_header.assert_called_with('a.b.c')

    def test_jwt_keys_are_cached(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": []},
        ]
        self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        calls = [c for c in self.mocked_get.call_args_list
                 if 'jwks' in c[0][0]]
        assert len(calls) == 1

    def test_fails_if_signature_verification_fails(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": []},
        ]
        self.mocked_jwt.get_unverified_header.side_effect = self.mocked_jwt.JWTError = ValueError
        payload = self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        assert payload is None

    def test_verifies_algo_header(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": []},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'unknown'}
        payload = self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        assert payload is None

    def test_fails_if_key_is_not_found(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": [{
                "kid": 2,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        payload = self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        assert payload is None

    def test_decodes_jwt_payload(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": [{
                "kid": 1,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        self.mocked_jwt.decode.return_value = {'sub': 'me'}
        payload = self.policy._verify_token(id_token='a.b.c', access_token='at', **self.verify_kw)
        assert payload['sub'] == 'me'

    def test_disables_at_hash_verification(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": [{
                "kid": 1,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        self.mocked_jwt.decode.return_value = {'sub': 'me'}

        self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)

        self.mocked_jwt.decode.assert_called_with('a.b.c', {'kid': 1}, algorithms=["RS256"],
                                                  audience='abc', issuer='https://idp',
                                                  options={"verify_at_hash": False},
                                                  access_token=None)

    def test_returns_none_if_jwt_verification_fails(self):
        self.mocked_get.return_value.json.side_effect = [
            {"keys": [{
                "kid": 1,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        self.mocked_jwt.ExpiredSignatureError = KeyError
        self.mocked_jwt.JWTClaimsError = ValueError

        self.mocked_jwt.decode.side_effect = ValueError("Claims error")
        payload = self.policy._verify_token(id_token='a.b.c', access_token='at', **self.verify_kw)
        assert payload is None

        self.mocked_jwt.decode.side_effect = KeyError("Claims error")
        payload = self.policy._verify_token(id_token='a.b.c', access_token='at', **self.verify_kw)
        assert payload is None

        self.mocked_jwt.decode.side_effect = IOError("will catch all")
        uid = self.policy._verify_token(id_token='a.b.c', access_token='at', **self.verify_kw)
        assert uid is None


class LoginViewTest(OpenIDWebTest):

    def test_returns_400_if_parameters_are_missing_or_bad(self):
        self.app.get('/openid/login', status=400)
        self.app.get('/openid/login', params={'callback': 'http://no-scope'}, status=400)
        self.app.get('/openid/login', params={'callback': 'bad', 'scope': 'openid'}, status=400)

    def test_redirects_to_the_identity_provider(self):
        params = {'callback': 'http://ui', 'scope': 'openid'}
        resp = self.app.get('/openid/login', params=params, status=307)
        location = resp.headers['Location']
        assert 'auth0.com/authorize?' in location
        assert '%2Fv1%2Fopenid%2Ftoken' in location
        assert 'scope=openid' in location
        assert 'client_id=abc' in location

    def test_callback_is_stored_in_cache(self):
        params = {'callback': 'http://ui', 'scope': 'openid'}
        with mock.patch('kinto.plugins.openid.views.random_bytes_hex') as m:
            m.return_value = 'key'
            self.app.get('/openid/login', params=params, status=307)

        cached = self.app.app.registry.cache.get('openid:state:key')
        assert cached == 'http://ui'


class TokenViewTest(OpenIDWebTest):

    def test_returns_400_if_parameters_are_missing_or_bad(self):
        self.app.get('/openid/token', status=400)
        self.app.get('/openid/token', params={'code': 'abc'}, status=400)
        self.app.get('/openid/token', params={'state': 'abc'}, status=400)

    def test_returns_400_if_state_is_invalid(self):
        self.app.get('/openid/token', params={'code': 'abc', 'state': 'abc'}, status=400)

    def test_code_is_traded_using_client_secret(self):
        self.app.app.registry.cache.set('openid:state:key', 'http://ui', ttl=100)
        with mock.patch('kinto.plugins.openid.views.requests.post') as m:
            m.return_value.text = '{"access_token": "token"}'
            self.app.get('/openid/token', params={'code': 'abc', 'state': 'key'})
            m.assert_called_with(
                'https://auth.mozilla.auth0.com/oauth/token',
                data={
                    'code': 'abc',
                    'client_id': 'abc',
                    'client_secret': 'xyz',
                    'redirect_uri': 'http://localhost/v1/openid/token?',
                    'grant_type': 'authorization_code'})

    def test_state_cannot_be_reused(self):
        self.app.app.registry.cache.set('openid:state:key', 'http://ui', ttl=100)
        with mock.patch('kinto.plugins.openid.views.requests.post') as m:
            m.return_value.text = '{"access_token": "token"}'
            self.app.get('/openid/token', params={'code': 'abc', 'state': 'key'})
            self.app.get('/openid/token', params={'code': 'abc', 'state': 'key'}, status=400)

    def test_redirects_to_callback_using_authorization_response(self):
        self.app.app.registry.cache.set('openid:state:key', 'http://ui/#token=', ttl=100)
        with mock.patch('kinto.plugins.openid.views.requests.post') as m:
            m.return_value.text = '{"access_token": "token"}'
            resp = self.app.get('/openid/token', params={'code': 'abc', 'state': 'key'},
                                status=307)
        location = resp.headers['Location']
        assert location == 'http://ui/#token=%7B%22access_token%22%3A%20%22token%22%7D'
