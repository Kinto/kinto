import mock

from cliquet import authentication
from cliquet import utils

from .support import BaseWebTest, DummyRequest, unittest


class AuthenticationPoliciesTest(BaseWebTest, unittest.TestCase):

    sample_url = '/mushrooms'
    sample_basicauth = {'Authorization': 'Basic bWF0OjE='}

    def test_basic_auth_is_accepted_by_default(self):
        app = self._get_test_app()
        app.get(self.sample_url, headers=self.sample_basicauth, status=200)

    def test_basic_auth_is_accepted_if_enabled_in_settings(self):
        app = self._get_test_app({'multiauth.policies': 'basicauth'})
        app.get(self.sample_url, headers=self.sample_basicauth, status=200)

    def test_basic_auth_is_accepted_if_enabled_with_old_setting(self):
        app = self._get_test_app({
            'multiauth.policies': 'dummy',
            'multiauth.policy.dummy.use': ('pyramid.authentication.'
                                           'RepozeWho1AuthenticationPolicy'),
            'cliquet.basic_auth_enabled': 'true'})
        app.get(self.sample_url, headers=self.sample_basicauth, status=200)

    def test_basic_auth_is_accepted_if_default_with_old_setting(self):
        app = self._get_test_app({'cliquet.basic_auth_enabled': 'true'})
        app.get(self.sample_url, headers=self.sample_basicauth, status=200)

    def test_basic_auth_is_declined_if_disabled_in_settings(self):
        app = self._get_test_app({
            'multiauth.policies': 'dummy',
            'multiauth.policy.dummy.use': ('pyramid.authentication.'
                                           'RepozeWho1AuthenticationPolicy')})
        app.get(self.sample_url, headers=self.sample_basicauth, status=401)

    def test_views_are_forbidden_if_unknown_auth_method(self):
        app = self._get_test_app({'multiauth.policies': 'basicauth'})
        self.headers['Authorization'] = 'Carrier'
        app.get(self.sample_url, headers=self.headers, status=401)
        self.headers['Authorization'] = 'Carrier pigeon'
        app.get(self.sample_url, headers=self.headers, status=401)


class BasicAuthenticationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = authentication.BasicAuthAuthenticationPolicy()
        self.request = DummyRequest()
        self.request.headers['Authorization'] = 'Basic bWF0Og=='

    def test_prefixes_users_with_basicauth(self):
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertTrue(user_id.startswith('basicauth_'))

    @mock.patch('cliquet.utils.hmac_digest')
    def test_userid_is_hashed(self, mocked):
        mocked.return_value = 'yeah'
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIn('yeah', user_id)

    def test_userid_is_built_using_password(self):
        auth_password = utils.encode64('user:secret1', encoding='ascii')
        self.request.headers['Authorization'] = 'Basic %s' % auth_password
        user_id1 = self.policy.unauthenticated_userid(self.request)

        auth_password = utils.encode64('user:secret2', encoding='ascii')
        self.request.headers['Authorization'] = 'Basic %s' % auth_password
        user_id2 = self.policy.unauthenticated_userid(self.request)

        self.assertNotEqual(user_id1, user_id2)

    def test_views_are_forbidden_if_basic_is_wrong(self):
        self.request.headers['Authorization'] = 'Basic abc'
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIsNone(user_id)

    def test_returns_none_if_username_is_empty(self):
        auth_password = utils.encode64(':secret', encoding='ascii')
        self.request.headers['Authorization'] = 'Basic %s' % auth_password
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIsNone(user_id)

    def test_providing_empty_password_is_supported(self):
        auth_password = utils.encode64('secret:', encoding='ascii')
        self.request.headers['Authorization'] = 'Basic %s' % auth_password
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIsNotNone(user_id)
