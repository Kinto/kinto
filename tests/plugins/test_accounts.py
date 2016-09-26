import unittest

from kinto.core.testing import get_user_headers

from .. import support


class AccountsWebTest(support.BaseWebTest, unittest.TestCase):

    def get_app_settings(self, extras=None):
        settings = super(AccountsWebTest, self).get_app_settings(extras)
        settings['includes'] = 'kinto.plugins.accounts'
        settings['multiauth.policies'] = 'account'
        # XXX: this should be a default setting.
        settings['multiauth.policy.account.use'] = ('kinto.plugins.accounts.authentication.'
                                                    'AccountsAuthenticationPolicy')
        return settings


class HelloViewTest(AccountsWebTest):

    def test_accounts_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('accounts', capabilities)


class AccountCreationTest(AccountsWebTest):

    def test_anyone_can_create_an_account(self):
        self.app.post_json('/accounts', {'data': {'id': 'alice', 'password': '123456'}},
                           status=201)

    def test_username_is_generated_if_not_provided(self):
        resp = self.app.post_json('/accounts', {'data': {'password': 's3cr3t'}})
        assert len(resp.json['data']['id']) == 8

    def test_account_can_be_created_with_put(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)

    def test_authentication_is_accepted_if_account_exists(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        resp = self.app.get('/', headers=get_user_headers('me', 'bouh'))
        assert resp.json['user']['id'] == 'account:me'

    def test_password_field_is_mandatory(self):
        self.app.post_json('/accounts', {'data': {'id': 'me'}}, status=400)

    def test_account_can_have_metadata(self):
        resp = self.app.post_json('/accounts',
                                  {'data': {'id': 'me', 'password': 'bouh', 'age': 42}},
                                  status=201)
        assert resp.json['data']['age'] == 42

    def test_cannot_create_account_if_already_exists(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        resp = self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                                  status=403)
        assert 'already exists' in resp.json['message']

    def test_returns_existing_account_if_authenticated(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           headers=get_user_headers('me', 'bouh'),
                           status=200)

    def test_cannot_create_other_account_if_authenticated(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        resp = self.app.post_json('/accounts', {'data': {'id': 'you', 'password': 'bouh'}},
                                  headers=get_user_headers('me', 'bouh'),
                                  status=400)
        assert 'do not match' in resp.json['message']


class AccountUpdateTest(AccountsWebTest):

    def setUp(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)

    def test_password_can_be_changed(self):
        self.app.put_json('/accounts/alice', {'data': {'password': 'bouh'}},
                          headers=get_user_headers('alice', '123456'),
                          status=200)

    def test_authentication_with_old_password_is_denied_after_change(self):
        self.app.put_json('/accounts/alice', {'data': {'password': 'bouh'}},
                          headers=get_user_headers('alice', '123456'),
                          status=200)
        self.app.get('/accounts/alice', headers=get_user_headers('alice', '123456'),
                     status=401)

    def test_authentication_with_new_password_is_accepted_after_change(self):
        self.app.put_json('/accounts/alice', {'data': {'password': 'bouh'}},
                          headers=get_user_headers('alice', '123456'),
                          status=200)
        self.app.get('/accounts/alice', headers=get_user_headers('alice', 'bouh'))

    def test_username_and_account_id_must_match(self):
        resp = self.app.patch_json('/accounts/alice', {'data': {'id': 'bob', 'password': 'bouh'}},
                                   headers=get_user_headers('alice', '123456'),
                                   status=400)
        assert 'does not match' in resp.json['message']

    def test_cannot_patch_unknown_account(self):
        resp = self.app.patch_json('/accounts/bob', {'data': {'password': 'bouh'}},
                                   headers=get_user_headers('alice', '123456'),
                                   status=404)
        assert 'Not Found' in resp.json['error']

    def test_cannot_patch_someone_else_account(self):
        self.app.put_json('/accounts/bob', {'data': {'password': 'bob'}}, status=201)
        resp = self.app.patch_json('/accounts/bob', {'data': {'password': 'bouh'}},
                                   headers=get_user_headers('alice', '123456'),
                                   status=400)
        assert 'do not match' in resp.json['message']

    def test_metadata_can_be_changed(self):
        resp = self.app.patch_json('/accounts/alice', {'data': {'age': 'captain'}},
                                   headers=get_user_headers('alice', '123456'))
        assert resp.json['data']['age'] == 'captain'


class AccountDeleteTest(AccountsWebTest):

    def setUp(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)

    def test_account_can_be_deleted(self):
        self.app.delete('/accounts/alice', headers=get_user_headers('alice', '123456'))

    def test_authentication_is_denied_after_delete(self):
        self.app.delete('/accounts/alice', headers=get_user_headers('alice', '123456'))
        self.app.get('/accounts/alice', headers=get_user_headers('alice', '123456'),
                     status=401)


class AccountViewsTest(AccountsWebTest):

    def setUp(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)
        self.app.put_json('/accounts/bob', {'data': {'password': 'azerty'}}, status=201)

    def test_account_detail_is_forbidden_if_anonymous(self):
        self.app.get('/accounts', status=401)
        self.app.get('/accounts/alice', status=401)

    def test_accounts_list_contains_only_one_record(self):
        resp = self.app.get('/accounts', headers=get_user_headers('alice', '123456'))
        assert len(resp.json['data']) == 1

    def test_account_record_can_be_obtained_if_authenticated(self):
        self.app.get('/accounts/alice', headers=get_user_headers('alice', '123456'))

    def test_cannot_obtain_someone_else_account(self):
        self.app.get('/accounts/bob', headers=get_user_headers('alice', '123456'),
                     status=403)

    def test_cannot_obtain_unknown_account(self):
        self.app.get('/accounts/jeanine', headers=get_user_headers('alice', '123456'),
                     status=403)
