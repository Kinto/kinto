from unittest import mock

from kinto.core import authentication
from kinto.core import utils
from kinto.core.testing import DummyRequest, unittest

from .support import BaseWebTest


class AuthenticationPoliciesTest(BaseWebTest, unittest.TestCase):
    def test_basic_auth_is_accepted_by_default(self):
        self.app.get(self.plural_url, headers=self.headers, status=200)
        # Check that the capability is exposed on the homepage.
        resp = self.app.get("/")
        assert "basicauth" in resp.json["capabilities"]

    def test_basic_auth_is_accepted_if_enabled_in_settings(self):
        app = self.make_app({"multiauth.policies": "basicauth"})
        app.get(self.plural_url, headers=self.headers, status=200)
        # Check that the capability is exposed on the homepage.
        resp = app.get("/")
        assert "basicauth" in resp.json["capabilities"]

    def test_basic_auth_is_declined_if_disabled_in_settings(self):
        app = self.make_app(
            {
                "multiauth.policies": "dummy",
                "multiauth.policy.dummy.use": (
                    "pyramid.authentication." "RepozeWho1AuthenticationPolicy"
                ),
            }
        )
        app.get(self.plural_url, headers=self.headers, status=401)
        # Check that the capability is exposed on the homepage.
        resp = app.get("/")
        assert "basicauth" not in resp.json["capabilities"]

    @mock.patch("kinto.core.authentication.BasicAuthAuthenticationPolicy")
    def test_policy_name_is_used(self, basicAuth):
        basicAuth.return_value.name = "foobar"
        app = self.make_app(
            {
                "multiauth.policies": "dummy",
                "multiauth.policy.dummy.use": (
                    "kinto.core.authentication." "BasicAuthAuthenticationPolicy"
                ),
            }
        )
        # Check that the policy uses its name rather than the settings prefix
        resp = app.get("/")
        assert resp.json["user"]["id"].startswith("foobar:")

    def test_views_are_forbidden_if_unknown_auth_method(self):
        app = self.make_app({"multiauth.policies": "basicauth"})
        self.headers["Authorization"] = "Carrier"
        app.get(self.plural_url, headers=self.headers, status=401)
        self.headers["Authorization"] = "Carrier pigeon"
        app.get(self.plural_url, headers=self.headers, status=401)

    def test_principals_are_fetched_from_permission_backend(self):
        patch = mock.patch(("tests.core.support." "AllowAuthorizationPolicy.permits"))
        self.addCleanup(patch.stop)
        mocked = patch.start()

        self.permission.add_user_principal(self.principal, "group:admin")
        self.app.get(self.plural_url, headers=self.headers)

        _, principals, _ = mocked.call_args[0]
        self.assertIn("group:admin", principals)

    def test_user_principals_are_cached_per_user(self):
        patch = mock.patch.object(
            self.permission, "get_user_principals", wraps=self.permission.get_user_principals
        )
        self.addCleanup(patch.stop)
        mocked = patch.start()
        batch = {
            "defaults": {"headers": self.headers, "path": "/mushrooms"},
            "requests": [
                {},
                {},
                {},
                {"headers": {"Authorization": "Basic Ym9iOg=="}},
                {"headers": {"Authorization": "Basic bWF0Og=="}},
            ],
        }
        self.app.post_json("/batch", batch)
        self.assertEqual(mocked.call_count, 3)


class BasicAuthenticationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = authentication.BasicAuthAuthenticationPolicy()
        self.request = DummyRequest()
        self.request.headers["Authorization"] = "Basic bWF0Og=="

    @mock.patch("kinto.core.utils.hmac_digest")
    def test_userid_is_hashed(self, mocked):
        mocked.return_value = "yeah"
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIn("yeah", user_id)

    def test_userid_is_built_using_password(self):
        auth_password = utils.encode64("user:secret1", encoding="ascii")
        self.request.headers["Authorization"] = "Basic {}".format(auth_password)
        user_id1 = self.policy.unauthenticated_userid(self.request)

        auth_password = utils.encode64("user:secret2", encoding="ascii")
        self.request.headers["Authorization"] = "Basic {}".format(auth_password)
        user_id2 = self.policy.unauthenticated_userid(self.request)

        self.assertNotEqual(user_id1, user_id2)

    def test_views_are_forbidden_if_basic_is_wrong(self):
        self.request.headers["Authorization"] = "Basic abc"
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIsNone(user_id)

    def test_returns_none_if_username_is_empty(self):
        auth_password = utils.encode64(":secret", encoding="ascii")
        self.request.headers["Authorization"] = "Basic {}".format(auth_password)
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIsNone(user_id)

    def test_providing_empty_password_is_supported(self):
        auth_password = utils.encode64("secret:", encoding="ascii")
        self.request.headers["Authorization"] = "Basic {}".format(auth_password)
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIsNotNone(user_id)
