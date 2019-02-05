import unittest
from unittest import mock

from kinto.core.testing import DummyRequest
from kinto.plugins.openid import OpenIDConnectPolicy
from kinto.plugins.openid.utils import fetch_openid_config

from .. import support


def get_openid_configuration(url):
    base_url = url.replace("/.well-known/openid-configuration", "")
    m = mock.Mock()
    m.json.return_value = {
        "issuer": "{base_url} issuer".format(base_url=base_url),
        "authorization_endpoint": "{base_url}/authorize".format(base_url=base_url),
        "userinfo_endpoint": "{base_url}/oauth/user".format(base_url=base_url),
        "token_endpoint": "{base_url}/oauth/token".format(base_url=base_url),
    }
    return m


class OpenIDWebTest(support.BaseWebTest, unittest.TestCase):
    @classmethod
    def make_app(cls, *args, **kwargs):
        with mock.patch("kinto.plugins.openid.requests.get") as get:
            get.side_effect = get_openid_configuration
            return super(OpenIDWebTest, cls).make_app(*args, **kwargs)

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        openid_policy = "kinto.plugins.openid.OpenIDConnectPolicy"
        settings["includes"] = "kinto.plugins.openid"
        settings["multiauth.policies"] = "auth0 google"
        settings["multiauth.policy.auth0.use"] = openid_policy
        settings["multiauth.policy.auth0.issuer"] = "https://auth.mozilla.auth0.com"
        settings["multiauth.policy.auth0.client_id"] = "abc"
        settings["multiauth.policy.auth0.client_secret"] = "xyz"

        settings["multiauth.policy.google.use"] = openid_policy
        settings["multiauth.policy.google.issuer"] = "https://accounts.google.com"
        settings["multiauth.policy.google.client_id"] = "123"
        settings["multiauth.policy.google.client_secret"] = "789"
        settings["multiauth.policy.google.userid_field"] = "email"
        return settings

    def test_openid_multiple_providers(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        providers = capabilities["openid"]["providers"]
        assert len(providers) == 2


class OpenIDWithoutPolicyTest(support.BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.openid"
        return settings

    def test_openid_capability_is_not_added(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        assert "openid" not in capabilities


class OpenIDOnePolicyTest(support.BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        openid_policy = "kinto.plugins.openid.OpenIDConnectPolicy"
        settings["includes"] = "kinto.plugins.openid"
        settings["multiauth.policies"] = "google"
        settings["multiauth.policy.auth0.use"] = openid_policy
        settings["multiauth.policy.auth0.issuer"] = "https://auth.mozilla.auth0.com"
        settings["multiauth.policy.auth0.client_id"] = "abc"
        settings["multiauth.policy.auth0.client_secret"] = "xyz"

        settings["multiauth.policy.google.use"] = openid_policy
        settings["multiauth.policy.google.issuer"] = "https://accounts.google.com"
        settings["multiauth.policy.google.client_id"] = "123"
        settings["multiauth.policy.google.client_secret"] = "789"
        settings["multiauth.policy.google.userid_field"] = "email"
        return settings

    def test_openid_one_provider(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        providers = capabilities["openid"]["providers"]
        assert len(providers) == 1

    def test_profile_is_exposed(self):
        key = "openid:verify:444c6694937007bbf494f155f6cb12139db4c4c6a926742f3fe0bb4b5d191aa3"
        profile = {"sub": "abcd", "email": "foobar@tld.com"}
        self.app.app.registry.cache.set(key, profile, ttl=30)
        with mock.patch("kinto.plugins.openid.utils.requests.get") as m:
            m.return_value.json.return_value = {
                "userinfo_endpoint": "http://uinfo",
                "jwks_uri": "https://jwks",
            }
            fetch_openid_config("https://fxa")

        resp = self.app.get("/", headers={"Authorization": "Bearer avrbnnbrbr"})
        assert "profile" in resp.json["user"]
        assert resp.json["user"]["profile"] == {"sub": "abcd", "email": "foobar@tld.com"}


class HelloViewTest(OpenIDWebTest):
    def test_openid_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        assert "openid" in capabilities
        assert len(capabilities["openid"]["providers"]) == 2
        assert "userinfo_endpoint" in capabilities["openid"]["providers"][0]
        assert "auth_path" in capabilities["openid"]["providers"][0]

    def test_openid_in_openapi(self):
        resp = self.app.get("/__api__")
        assert "auth0" in resp.json["securityDefinitions"]
        auth = resp.json["securityDefinitions"]["auth0"]["authorizationUrl"]
        assert auth == "https://auth.mozilla.auth0.com/authorize"


class PolicyTest(unittest.TestCase):
    def setUp(self):
        mocked = mock.patch("kinto.plugins.openid.requests.get")
        self.mocked_get = mocked.start()
        self.addCleanup(mocked.stop)

        self.policy = OpenIDConnectPolicy(issuer="https://idp", client_id="abc")

        self.request = DummyRequest()
        self.request.registry.cache.get.return_value = None

        mocked = mock.patch.object(self.policy, "_verify_token")
        self.verify = mocked.start()
        self.addCleanup(mocked.stop)
        self.verify.return_value = {"sub": "userid"}

    def test_returns_none_if_no_authorization(self):
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_returns_header_type_in_forget(self):
        h = self.policy.forget(self.request)
        assert "Bearer " in h[0][1]

    def test_header_type_can_be_configured(self):
        self.policy.header_type = "bearer+oidc"
        h = self.policy.forget(self.request)
        assert "bearer+oidc " in h[0][1]

    def test_returns_none_if_no_authorization_prefix(self):
        self.request.headers["Authorization"] = "avrbnnbrbr"
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_returns_none_if_bad_prefix(self):
        self.request.headers["Authorization"] = "Basic avrbnnbrbr"
        assert self.policy.unauthenticated_userid(self.request) is None

    def test_can_specify_only_opaque_access_token(self):
        self.request.headers["Authorization"] = "Bearer xyz"
        assert self.policy.unauthenticated_userid(self.request) == "userid"
        self.verify.assert_called_with("xyz")

    def test_returns_none_if_no_cache_and_invalid_access_token(self):
        self.request.headers["Authorization"] = "Bearer xyz"
        self.request.registry.cache.get.return_value = None
        self.verify.return_value = None
        assert self.policy.unauthenticated_userid(self.request) is None
        assert not self.request.registry.cache.set.called

    def test_payload_is_read_from_cache(self):
        self.request.headers["Authorization"] = "Bearer xyz"
        self.request.registry.cache.get.return_value = {"sub": "me"}
        assert self.policy.unauthenticated_userid(self.request) == "me"

    def test_payload_is_stored_in_cache(self):
        self.request.headers["Authorization"] = "Bearer xyz"
        assert self.policy.unauthenticated_userid(self.request) == "userid"
        assert self.request.registry.cache.set.called

    def test_payload_is_read_from_cache_but_differently_by_access_token(self):
        # State to keep track of cache keys queried.
        cache_keys_used = []

        def mocked_cache_get(cache_key):
            # This makes sure the same cache key is not used twice
            assert cache_key not in cache_keys_used
            cache_keys_used.append(cache_key)
            if len(cache_keys_used) == 1:
                return {"sub": "me"}
            elif len(cache_keys_used) == 2:
                return {"sub": "you"}

        self.request.registry.cache.get.side_effect = mocked_cache_get

        self.request.headers["Authorization"] = "Bearer xyz"
        assert self.policy.unauthenticated_userid(self.request) == "me"

        # Change the Authorization header the second time
        self.request.headers["Authorization"] = "Bearer abc"
        assert self.policy.unauthenticated_userid(self.request) == "you"


class VerifyTokenTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Populate OpenID config cache.
        with mock.patch("kinto.plugins.openid.utils.requests.get") as m:
            m.return_value.json.return_value = {
                "userinfo_endpoint": "http://uinfo",
                "jwks_uri": "https://jwks",
            }
            fetch_openid_config("https://fxa")

    def setUp(self):
        mocked = mock.patch("kinto.plugins.openid.requests.get")
        self.mocked_get = mocked.start()
        self.addCleanup(mocked.stop)

        self.policy = OpenIDConnectPolicy(issuer="https://fxa", client_id="abc")

    def test_fetches_userinfo_if_id_token_is_none(self):
        self.mocked_get.return_value.json.side_effect = [{"sub": "me"}]
        payload = self.policy._verify_token(access_token="abc")
        assert payload["sub"] == "me"

    def test_returns_none_if_fetching_userinfo_fails(self):
        self.mocked_get.return_value.raise_for_status.side_effect = ValueError
        payload = self.policy._verify_token(access_token="abc")
        assert payload is None


class LoginViewTest(OpenIDWebTest):
    def test_returns_400_if_parameters_are_missing_or_bad(self):
        self.app.get("/openid/auth0/login", status=400)
        self.app.get("/openid/auth0/login", params={"callback": "http://no-scope"}, status=400)
        self.app.get(
            "/openid/auth0/login", params={"callback": "bad", "scope": "openid"}, status=400
        )

    def test_returns_400_if_provider_is_unknown(self):
        self.app.get("/openid/fxa/login", status=400)

    def test_returns_400_if_email_is_not_in_scope_when_userid_field_is_email(self):
        scope = "openid"
        cb = "http://ui.kinto.example.com"
        self.app.get("/openid/auth0/login", params={"callback": cb, "scope": scope}, status=307)
        # See config above (email is userid field)
        self.app.get("/openid/google/login", params={"callback": cb, "scope": scope}, status=400)

    def test_returns_400_if_prompt_is_not_recognized(self):
        scope = "openid"
        cb = "http://ui"
        self.app.get(
            "/openid/auth0/login",
            params={"callback": cb, "scope": scope, "prompt": "junk"},
            status=400,
        )

    def test_redirects_to_the_identity_provider(self):
        params = {"callback": "http://ui.kinto.example.com", "scope": "openid"}
        resp = self.app.get("/openid/auth0/login", params=params, status=307)
        location = resp.headers["Location"]
        assert "auth0.com/authorize?" in location
        assert "%2Fv1%2Fopenid%2Fauth0%2Ftoken" in location
        assert "scope=openid" in location
        assert "client_id=abc" in location

    def test_redirects_to_the_identity_provider_with_prompt_none(self):
        params = {"callback": "http://ui.kinto.example.com", "scope": "openid", "prompt": "none"}
        resp = self.app.get("/openid/auth0/login", params=params, status=307)
        location = resp.headers["Location"]
        assert "auth0.com/authorize?" in location
        assert "%2Fv1%2Fopenid%2Fauth0%2Ftoken" in location
        assert "scope=openid" in location
        assert "client_id=abc" in location
        assert "prompt=none" in location

    def test_callback_is_stored_in_cache(self):
        params = {"callback": "http://ui.kinto.example.com", "scope": "openid"}
        with mock.patch("kinto.plugins.openid.views.random_bytes_hex") as m:
            m.return_value = "key"
            self.app.get("/openid/auth0/login", params=params, status=307)

        cached = self.app.app.registry.cache.get("openid:state:key")
        assert cached == "http://ui.kinto.example.com"


class TokenViewTest(OpenIDWebTest):
    def test_returns_400_if_parameters_are_missing_or_bad(self):
        self.app.get("/openid/auth0/token", status=400)
        self.app.get("/openid/auth0/token", params={"code": "abc"}, status=400)
        self.app.get("/openid/auth0/token", params={"state": "abc"}, status=400)

    def test_returns_400_if_provider_is_unknown(self):
        self.app.get("/openid/fxa/token", status=400)

    def test_returns_400_if_state_is_invalid(self):
        self.app.get("/openid/auth0/token", params={"code": "abc", "state": "abc"}, status=400)

    def test_code_is_traded_using_client_secret(self):
        self.app.app.registry.cache.set("openid:state:key", "http://ui", ttl=100)
        with mock.patch("kinto.plugins.openid.views.requests.post") as m:
            m.return_value.text = '{"access_token": "token"}'
            self.app.get("/openid/auth0/token", params={"code": "abc", "state": "key"})
            m.assert_called_with(
                "https://auth.mozilla.auth0.com/oauth/token",
                data={
                    "code": "abc",
                    "client_id": "abc",
                    "client_secret": "xyz",
                    "redirect_uri": "http://localhost/v1/openid/auth0/token",
                    "grant_type": "authorization_code",
                },
            )

    def test_state_cannot_be_reused(self):
        self.app.app.registry.cache.set("openid:state:key", "http://ui", ttl=100)
        with mock.patch("kinto.plugins.openid.views.requests.post") as m:
            m.return_value.text = '{"access_token": "token"}'
            self.app.get("/openid/auth0/token", params={"code": "abc", "state": "key"})
            self.app.get("/openid/auth0/token", params={"code": "abc", "state": "key"}, status=400)

    def test_redirects_to_callback_using_authorization_response(self):
        self.app.app.registry.cache.set("openid:state:key", "http://ui/#token=", ttl=100)
        with mock.patch("kinto.plugins.openid.views.requests.post") as m:
            m.return_value.text = '{"access_token": "token"}'
            resp = self.app.get(
                "/openid/auth0/token", params={"code": "abc", "state": "key"}, status=307
            )
        location = resp.headers["Location"]
        assert location == "http://ui/#token=eyJhY2Nlc3NfdG9rZW4iOiAidG9rZW4ifQ%3D%3D"
