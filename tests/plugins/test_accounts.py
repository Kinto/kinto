# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from kinto.core.testing import get_user_headers
from pyramid.exceptions import ConfigurationError

from .. import support


class AccountsWebTest(support.BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {}
        extras.setdefault('multiauth.policies', 'account')
        extras.setdefault('includes', 'kinto.plugins.accounts')
        extras.setdefault('account_create_principals', 'system.Everyone')
        # XXX: this should be a default setting.
        extras.setdefault('multiauth.policy.account.use', 'kinto.plugins.accounts.authentication.'
                                                          'AccountsAuthenticationPolicy')
        return super().get_app_settings(extras)


class HelloViewTest(AccountsWebTest):

    def test_accounts_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('accounts', capabilities)


class AccountCreationTest(AccountsWebTest):

    def test_anyone_can_create_an_account(self):
        self.app.post_json('/accounts', {'data': {'id': 'alice', 'password': '12éé6'}},
                           status=201)

    def test_account_can_be_created_with_put(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)

    def test_password_is_stored_encrypted(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)
        stored = self.app.app.registry.storage.get(parent_id='alice',
                                                   collection_id='account',
                                                   object_id='alice')
        assert stored['password'] != '123456'

    def test_authentication_is_accepted_if_account_exists(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        resp = self.app.get('/', headers=get_user_headers('me', 'bouh'))
        assert resp.json['user']['id'] == 'account:me'

    def test_password_field_is_mandatory(self):
        self.app.post_json('/accounts', {'data': {'id': 'me'}}, status=400)

    def test_id_field_is_mandatory(self):
        self.app.post_json('/accounts', {'data': {'password': 'pass'}}, status=400)

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

    def test_username_and_account_id_must_match(self):
        resp = self.app.put_json('/accounts/alice', {'data': {'id': 'bob', 'password': 'bouh'}},
                                 status=400)
        assert 'does not match' in resp.json['message']

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
        self.app.patch_json('/accounts/bob', {'data': {'password': 'bouh'}},
                            headers=get_user_headers('alice', '123456'),
                            status=403)

    def test_cannot_patch_someone_else_account(self):
        self.app.put_json('/accounts/bob', {'data': {'password': 'bob'}}, status=201)
        self.app.patch_json('/accounts/bob', {'data': {'password': 'bouh'}},
                            headers=get_user_headers('alice', '123456'),
                            status=403)

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

    def test_account_list_is_forbidden_if_anonymous(self):
        self.app.get('/accounts', status=401)

    def test_account_detail_is_forbidden_if_anonymous(self):
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


class AdminTest(AccountsWebTest):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['account_write_principals'] = 'account:admin'
        settings['account_read_principals'] = 'account:admin'
        return settings

    def setUp(self):
        self.app.put_json('/accounts/admin', {'data': {'password': '123456'}}, status=201)
        self.admin_headers = get_user_headers('admin', '123456')

        self.app.put_json('/accounts/bob', {'data': {'password': '987654'}}, status=201)

    def test_admin_can_get_other_accounts(self):
        self.app.put_json('/accounts/alice', {'data': {'password': 'azerty'}}, status=201)

        resp = self.app.get('/accounts/alice', headers=get_user_headers('alice', 'azerty'))
        assert resp.json['data']['id'] == 'alice'

    def test_admin_can_delete_other_accounts(self):
        self.app.delete_json('/accounts/bob', headers=self.admin_headers)
        self.app.get('/accounts/bob', headers=get_user_headers('bob', '987654'),
                     status=401)

    def test_admin_can_set_others_password(self):
        self.app.patch_json('/accounts/bob', {'data': {'password': 'bouh'}},
                            headers=self.admin_headers)
        self.app.get('/accounts/bob', headers=get_user_headers('bob', '987654'),
                     status=401)
        self.app.get('/accounts/bob', headers=get_user_headers('bob', 'bouh'))

    def test_admin_can_retrieve_accounts_list(self):
        self.app.put_json('/accounts/alice', {'data': {'password': 'azerty'}}, status=201)

        resp = self.app.get('/accounts', headers=self.admin_headers)
        usernames = [r['id'] for r in resp.json['data']]
        assert sorted(usernames) == ['admin', 'alice', 'bob']

    def test_user_created_by_admin_with_put_can_see_her_record(self):
        self.app.put_json('/accounts/alice',
                          {'data': {'password': 'bouh'}},
                          headers=self.admin_headers)

        resp = self.app.get('/accounts/alice', headers=get_user_headers('alice', 'bouh'))
        assert resp.json['permissions'] == {'write': ['account:alice']}

    def test_user_created_by_admin_with_post_can_see_her_record(self):
        self.app.post_json('/accounts',
                           {'data': {'id': 'alice', 'password': 'bouh'}},
                           headers=self.admin_headers)

        resp = self.app.get('/accounts/alice', headers=get_user_headers('alice', 'bouh'))
        assert resp.json['permissions'] == {'write': ['account:alice']}

    def test_user_created_by_admin_can_delete_her_record(self):
        self.app.post_json('/accounts',
                           {'data': {'id': 'alice', 'password': 'bouh'}},
                           headers=self.admin_headers)

        self.app.delete('/accounts/alice', headers=get_user_headers('alice', 'bouh'))


class WithBasicAuthTest(AccountsWebTest):

    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {'multiauth.policies': 'account basicauth'}
        return super().get_app_settings(extras)

    def test_password_field_is_mandatory(self):
        self.app.post_json('/accounts', {'data': {'id': 'me'}}, status=400)

    def test_id_field_is_mandatory(self):
        self.app.post_json('/accounts', {'data': {'password': 'pass'}}, status=400)

    def test_fallsback_on_basicauth(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bleh'}})

        resp = self.app.get('/', headers=get_user_headers('me', 'wrong'))
        assert 'basicauth' in resp.json['user']['id']

        resp = self.app.get('/', headers=get_user_headers('me', 'bleh'))
        assert 'account' in resp.json['user']['id']

    def test_raise_configuration_if_wrong_error(self):
        with self.assertRaises(ConfigurationError):
            self.make_app({'multiauth.policies': 'basicauth account'})
