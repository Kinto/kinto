import unittest
import mock

from kinto.core.testing import DummyRequest
from kinto.plugins.openid import OpenIDConnectPolicy

from .. import support


class OpenIDWebTest(support.BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['includes'] = 'kinto.plugins.openid'
        settings['oidc.issuer_url'] = 'https://auth.mozilla.auth0.com'
        settings['oidc.audience'] = 'abc'
        return settings


class HelloViewTest(OpenIDWebTest):

    def test_openid_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('openid', capabilities)
        self.assertIn('authorization_endpoint', capabilities['openid'])

    def test_openid_in_openapi(self):
        pass


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = OpenIDConnectPolicy()
        self.request = DummyRequest()
        self.request.registry.settings["oidc.issuer_url"] = 'https://idp'
        self.request.registry.settings["oidc.audience"] = 'abc'
        mocked = mock.patch.object(self.policy, '_verify_token')
        self.verify = mocked.start()
        self.addCleanup(mocked.stop)
        self.verify.return_value = 'userid'

    def test_returns_none_if_no_authorization(self):
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_returns_none_if_no_authorization_prefix(self):
        self.request.headers['Authorization'] = 'avrbnnbrbr'
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_returns_none_if_bad_prefix(self):
        self.request.headers['Authorization'] = 'Basic avrbnnbrbr'
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_can_specify_both_id_and_access_token(self):
        self.request.headers['Authorization'] = 'Bearer+OIDC id_token=jwt, access_token=bearer'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        self.verify.assert_called_with('https://idp', 'abc', 'jwt', 'bearer')

    def test_can_specify_jwt_token(self):
        self.request.headers['Authorization'] = 'Bearer+OIDC j.w.t'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        self.verify.assert_called_with('https://idp', 'abc', 'j.w.t', None)

    def test_can_specify_only_opaque_access_token(self):
        self.request.headers['Authorization'] = 'Bearer+OIDC xyz'
        assert self.policy.unauthenticated_userid(self.request) == 'userid'
        self.verify.assert_called_with('https://idp', 'abc', None, 'xyz')


class VerifyTokenTest(unittest.TestCase):
    def setUp(self):
        self.policy = OpenIDConnectPolicy()

        mocked = mock.patch('kinto.plugins.openid.requests.get')
        self.mocked_get = mocked.start()
        self.addCleanup(mocked.stop)

        mocked = mock.patch('kinto.plugins.openid.jwt')
        self.mocked_jwt = mocked.start()
        self.addCleanup(mocked.stop)

        self.verify_kw = dict(issuer='https://idp', audience='abc')

    def test_fetches_openid_config(self):
        self.policy._verify_token(id_token=None, access_token='abc', **self.verify_kw)
        self.mocked_get.assert_any_call('https://idp/.well-known/openid-configuration')

    def test_fetches_userinfo_if_id_token_is_none(self):
        self.mocked_get.return_value.json.side_effect = [
            {'userinfo_endpoint': 'http://uinfo'},
            {"sub": "me"},
        ]
        uid = self.policy._verify_token(id_token=None, access_token='abc', **self.verify_kw)
        assert uid == "me"

    def test_verifies_jwt_headers(self):
        self.mocked_get.return_value.json.side_effect = [
            {'userinfo_endpoint': 'http://uinfo', 'jwks_uri': ''},
            {"keys": []},
        ]
        self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        self.mocked_jwt.get_unverified_header.assert_called_with('a.b.c')

    def test_verifies_algo_header(self):
        self.mocked_get.return_value.json.side_effect = [
            {'userinfo_endpoint': 'http://uinfo', 'jwks_uri': ''},
            {"keys": []},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'unknown'}
        uid = self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        assert uid is None

    def test_fails_if_key_is_not_found(self):
        self.mocked_get.return_value.json.side_effect = [
            {'userinfo_endpoint': 'http://uinfo', 'jwks_uri': ''},
            {"keys": [{
                "kid": 2,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        uid = self.policy._verify_token(id_token='a.b.c', access_token=None, **self.verify_kw)
        assert uid is None

    def test_decodes_jwt_payload(self):
        self.mocked_get.return_value.json.side_effect = [
            {'userinfo_endpoint': 'http://uinfo', 'jwks_uri': ''},
            {"keys": [{
                "kid": 1,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        self.mocked_jwt.decode.return_value = {'sub': 'me'}
        uid = self.policy._verify_token(id_token='a.b.c', access_token='at', **self.verify_kw)
        assert uid == 'me'

    def test_disables_at_hash_verification(self):
        self.mocked_get.return_value.json.side_effect = [
            {'userinfo_endpoint': 'http://uinfo', 'jwks_uri': ''},
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
            {'userinfo_endpoint': 'http://uinfo', 'jwks_uri': ''},
            {"keys": [{
                "kid": 1,
            }]},
        ]
        self.mocked_jwt.get_unverified_header.return_value = {'alg': 'RS256', 'kid': 1}
        self.mocked_jwt.ExpiredSignatureError = self.mocked_jwt.JWTClaimsError = ValueError
        self.mocked_jwt.decode.side_effect = ValueError("Claims error")
        uid = self.policy._verify_token(id_token='a.b.c', access_token='at', **self.verify_kw)
        assert uid is None
