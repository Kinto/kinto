# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import mock
import unittest

from kinto.core import utils
from kinto.core.testing import get_user_headers
from pyramid.exceptions import ConfigurationError

from kinto.plugins.accounts import scripts, ACCOUNT_CACHE_KEY
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

    def test_id_can_be_email(self):
        self.app.put_json('/accounts/alice@example.com', {'data': {'password': '123456'}},
                          status=201)

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

    def test_authentication_does_not_call_bcrypt_twice(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        with mock.patch('kinto.plugins.accounts.authentication.bcrypt') as mocked_bcrypt:
            resp = self.app.get('/', headers=get_user_headers('me', 'bouh'))
            assert resp.json['user']['id'] == 'account:me'

            resp = self.app.get('/', headers=get_user_headers('me', 'bouh'))
            assert resp.json['user']['id'] == 'account:me'

            mocked_bcrypt.checkpw.assert_called_once()

    def test_authentication_checks_bcrypt_again_if_password_changes(self):
        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        with mock.patch('kinto.plugins.accounts.authentication.bcrypt') as mocked_bcrypt:
            resp = self.app.get('/', headers=get_user_headers('me', 'bouh'))
            assert resp.json['user']['id'] == 'account:me'

            self.app.patch_json('/accounts/me', {'data': {'password': 'blah'}},
                                status=200, headers=get_user_headers('me', 'bouh'))

            resp = self.app.get('/', headers=get_user_headers('me', 'blah'))
            assert resp.json['user']['id'] == 'account:me'

            assert mocked_bcrypt.checkpw.call_count == 2

    def test_authentication_refresh_the_cache_each_time_we_authenticate(self):
        hmac_secret = self.app.app.registry.settings['userid_hmac_secret']
        cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_CACHE_KEY.format('me'))

        self.app.post_json('/accounts', {'data': {'id': 'me', 'password': 'bouh'}},
                           status=201)
        resp = self.app.get('/', headers=get_user_headers('me', 'bouh'))
        assert resp.json['user']['id'] == 'account:me'

        self.app.app.registry.cache.expire(cache_key, 10)

        resp = self.app.get('/', headers=get_user_headers('me', 'blah'))
        assert resp.json['user']['id'] == 'account:me'

        assert self.app.app.registry.cache.ttl(cache_key) >= 20


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


class PermissionsEndpointTest(AccountsWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['experimental_permissions_endpoint'] = 'True'
        return settings

    def setUp(self):
        self.app.put_json('/accounts/alice', {'data': {'password': '123456'}}, status=201)
        self.headers = get_user_headers('alice', '123456')
        self.app.put('/buckets/a', headers=self.headers)
        self.app.put('/buckets/a/collections/b', headers=self.headers)
        self.app.put('/buckets/a/collections/b/records/c', headers=self.headers)

    def test_permissions_endpoint_is_compatible_with_accounts_plugin(self):
        resp = self.app.get('/permissions', headers=self.headers)
        uris = [r["uri"] for r in resp.json["data"]]
        assert uris == ['/buckets/a/collections/b/records/c',
                        '/buckets/a/collections/b',
                        '/buckets/a',
                        '/accounts/alice']


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


class CheckAdminCreateTest(AccountsWebTest):
    def test_raise_if_create_but_no_write(self):
        with self.assertRaises(ConfigurationError):
            self.make_app({'account_create_principals': 'account:admin'})


class CreateOtherUserTest(AccountsWebTest):
    def setUp(self):
        self.app.put_json('/accounts/bob', {'data': {'password': '123456'}}, status=201)
        self.bob_headers = get_user_headers('bob', '123456')

    def test_create_other_id_is_still_required(self):
        self.app.post_json('/accounts', {'data': {'password': 'azerty'}}, status=400,
                           headers=self.bob_headers)

    def test_create_other_forbidden_without_write(self):
        self.app.put_json('/accounts/alice', {'data': {'password': 'azerty'}}, status=400,
                          headers=self.bob_headers)


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


class HawkSessionTest(AccountsWebTest):
    def setUp(self):
        creds = {'id': 'alice', 'password': '12éé6'}
        self.app.post_json('/accounts', {'data': creds}, status=201)
        self.account_creds = creds

    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {'multiauth.policies': 'hawkauth'}
            extras.setdefault('includes', 'kinto.plugins.accounts kinto.plugins.hawk')
            extras.setdefault(
                'multiauth.policy.hawkauth.use', 
                'kinto.plugins.hawk.authentication.HawkAuthenticationPolicy')

        return super().get_app_settings(extras)

    def test_request_hawk_session_returns_token_in_header(self):
        resp = self.app.post('/accounts/alice/hawk-sessions')
        assert 'Hawk-Session-Token' in resp.headers 
        assert len(resp.headers['Hawk-Session-Token']) == 64

    def test_request_hawk_session_wrong_account_id_returns_404(self):
        resp = self.app.post('/accounts/BAD_ACCOUNT/hawk-sessions', status=404)

    def test_request_hawk_session_saves_creds_to_account(self):
        resp = self.app.post('/accounts/alice/hawk-sessions')
        token = resp.headers['Hawk-Session-Token']
        account = request.registry.storage.get(parent_id='alice',
                                               collection_id='account',
                                               object_id='alice')
        #TODO get client id from the token and test that it has been
        # saved on the account record, along with creds and expiration
        # date

    def test_request_hawk_session_expires_session_after_date_setting(self):
        pass

    def test_hawk_session_expiration_date_is_overidden_by_setting(self):
        pass

    def test_request_remove_hawk_sessions_deletes_all_sessions(self):
        pass

    def test_request_remove_hawk_session_current_only(self):
        pass

    def test_hawk_auth_must_be_enabled(self):
        pass



class CreateUserTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()
        self.registry.settings = {
            "includes": "kinto.plugins.accounts",
        }

    def test_create_user_in_read_only_displays_an_error(self):
        with mock.patch('kinto.plugins.accounts.scripts.logger') as mocked:
            self.registry.settings['readonly'] = 'true'
            code = scripts.create_user({'registry': self.registry})
            assert code == 51
            mocked.error.assert_called_once_with('Cannot create a user with '
                                                 'a readonly server.')

    def test_create_user_when_not_included_displays_an_error(self):
        with mock.patch('kinto.plugins.accounts.scripts.logger') as mocked:
            self.registry.settings['includes'] = ''
            code = scripts.create_user({'registry': self.registry})
            assert code == 52
            mocked.error.assert_called_once_with('Cannot create a user when the accounts '
                                                 'plugin is not installed.')

    def test_create_user_with_an_invalid_username_and_password_confirmation_recovers(self):
        with mock.patch('kinto.plugins.accounts.scripts.input', side_effect=["&zert", "username"]):
            with mock.patch('kinto.plugins.accounts.scripts.getpass.getpass', side_effect=[
                    "password", "p4ssw0rd", "password", "password"]):
                code = scripts.create_user({'registry': self.registry}, None, None)
                self.registry.storage.update.assert_called_once()
                self.registry.permission.add_principal_to_ace.assert_called_with(
                    "/accounts/username", "write", "account:username")
                assert code == 0

    def test_create_user_with_a_valid_username_and_password_confirmation(self):
        with mock.patch('kinto.plugins.accounts.scripts.input', return_value="username"):
            with mock.patch('kinto.plugins.accounts.scripts.getpass.getpass',
                            return_value="password"):
                code = scripts.create_user({'registry': self.registry})
                self.registry.storage.update.assert_called_once()
                self.registry.permission.add_principal_to_ace.assert_called_with(
                    "/accounts/username", "write", "account:username")
                assert code == 0

    def test_create_user_with_valid_username_and_password_parameters(self):
        code = scripts.create_user({'registry': self.registry}, "username", "password")
        self.registry.storage.update.assert_called_once()
        self.registry.permission.add_principal_to_ace.assert_called_with(
            "/accounts/username", "write", "account:username")
        assert code == 0

    def test_create_user_aborted_by_eof(self):
        with mock.patch('kinto.plugins.accounts.scripts.input', side_effect=EOFError):
            code = scripts.create_user({'registry': self.registry})
            assert code == 53
