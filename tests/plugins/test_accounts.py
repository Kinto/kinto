import unittest
import uuid
from unittest import mock

import bcrypt
from pyramid.exceptions import ConfigurationError
from pyramid_mailer import get_mailer

from kinto.core import utils
from kinto.core.events import ACTIONS, ResourceChanged
from kinto.core.testing import DummyRequest, get_user_headers
from kinto.plugins.accounts import ACCOUNT_CACHE_KEY, scripts
from kinto.plugins.accounts.utils import (
    get_cached_reset_password,
    get_cached_validation_key,
    hash_password,
)
from kinto.plugins.accounts.views import on_account_created
from kinto.plugins.accounts.views.validation import on_account_activated

from .. import support


class AccountsWebTest(support.BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {}
        extras.setdefault("multiauth.policies", "account")
        extras.setdefault("includes", "kinto.plugins.accounts")
        extras.setdefault("account_create_principals", "system.Everyone")
        # XXX: this should be a default setting.
        extras.setdefault(
            "multiauth.policy.account.use",
            "kinto.plugins.accounts.authentication." "AccountsAuthenticationPolicy",
        )
        extras.setdefault("account_cache_ttl_seconds", "30")
        return super().get_app_settings(extras)


class AccountsValidationWebTest(AccountsWebTest):
    def setUp(self):
        self.mailer = get_mailer(self.app.app.registry)
        self.mailer.outbox = []  # Reset the outbox before each test.

    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {}
        # Enable the account validation option.
        extras.setdefault("account_validation", True)
        # Use a testing mailer.
        extras.setdefault("mail.mailer", "testing")
        # Email templates for the user creation.
        extras.setdefault(
            "account_validation.email_subject_template", "{name}, activate your account {id}"
        )
        extras.setdefault(
            "account_validation.email_body_template",
            "{activation-form-url}/{id}/{activation-key} {bad-key}",
        )
        # Email templates for the user validated confirmation.
        extras.setdefault(
            "account_validation.email_confirmation_subject_template",
            "{name}, your account {id} is now active",
        )
        extras.setdefault(
            "account_validation.email_confirmation_body_template",
            "Your account {id} has been successfully activated. Connect to {homepage}",
        )
        # Email templates for the reset password.
        extras.setdefault(
            "account_validation.email_reset_password_subject_template",
            "{name}, here is a temporary reset password for {id}",
        )
        extras.setdefault(
            "account_validation.email_reset_password_body_template",
            "You can use this temporary reset password {reset-password} to change your account {id} password",
        )
        return super().get_app_settings(extras)


class BadAccountsConfigTest(support.BaseWebTest, unittest.TestCase):
    def test_raise_configuration_if_accounts_not_mentioned(self):
        with self.assertRaises(ConfigurationError) as cm:
            self.make_app(
                {"includes": "kinto.plugins.accounts", "multiauth.policies": "basicauth"}
            )
        assert "Account policy missing" in str(cm.exception)


class HelloViewTest(AccountsWebTest):
    def test_accounts_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("accounts", capabilities)


class HelloActivationViewTest(AccountsValidationWebTest):
    def test_account_validation_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("accounts", capabilities)
        self.assertIn("validation_enabled", capabilities["accounts"])
        self.assertTrue(capabilities["accounts"]["validation_enabled"])


class AccountCreationTest(AccountsWebTest):
    def test_anyone_can_create_an_account(self):
        self.app.post_json("/accounts", {"data": {"id": "alice", "password": "12éé6"}}, status=201)

    def test_account_can_be_created_with_put(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "123456"}}, status=201)

    def test_password_is_stored_encrypted(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "123456"}}, status=201)
        stored = self.app.app.registry.storage.get(
            parent_id="alice", resource_name="account", object_id="alice"
        )
        assert stored["password"] != "123456"

    def test_authentication_is_accepted_if_account_exists(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        resp = self.app.get("/", headers=get_user_headers("me", "bouh"))
        assert resp.json["user"]["id"] == "account:me"

    def test_password_field_is_mandatory(self):
        self.app.post_json("/accounts", {"data": {"id": "me"}}, status=400)

    def test_id_field_is_mandatory(self):
        self.app.post_json("/accounts", {"data": {"password": "pass"}}, status=400)

    def test_id_can_be_email(self):
        self.app.put_json(
            "/accounts/alice+test@example.com", {"data": {"password": "123456"}}, status=201
        )

    def test_account_can_have_metadata(self):
        resp = self.app.post_json(
            "/accounts", {"data": {"id": "me", "password": "bouh", "age": 42}}, status=201
        )
        assert resp.json["data"]["age"] == 42

    def test_cannot_create_account_if_already_exists(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "not read"}}, status=401)

    def test_username_and_account_id_must_match(self):
        resp = self.app.put_json(
            "/accounts/alice", {"data": {"id": "bob", "password": "bouh"}}, status=400
        )
        assert "does not match" in resp.json["message"]

    def test_returns_existing_account_if_authenticated(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        self.app.post_json(
            "/accounts",
            {"data": {"id": "me", "password": "bouh"}},
            headers=get_user_headers("me", "bouh"),
            status=200,
        )

    def test_cannot_create_other_account_if_authenticated(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        resp = self.app.post_json(
            "/accounts",
            {"data": {"id": "you", "password": "bouh"}},
            headers=get_user_headers("me", "bouh"),
            status=400,
        )
        assert "do not match" in resp.json["message"]

    def test_authentication_does_not_call_bcrypt_twice(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        with mock.patch("kinto.plugins.accounts.authentication.bcrypt") as mocked_bcrypt:
            resp = self.app.get("/", headers=get_user_headers("me", "bouh"))
            assert resp.json["user"]["id"] == "account:me"

            resp = self.app.get("/", headers=get_user_headers("me", "bouh"))
            assert resp.json["user"]["id"] == "account:me"

            assert mocked_bcrypt.checkpw.call_count == 1

    def test_authentication_checks_bcrypt_again_if_password_changes(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        with mock.patch("kinto.plugins.accounts.authentication.bcrypt") as mocked_bcrypt:
            resp = self.app.get("/", headers=get_user_headers("me", "bouh"))
            assert resp.json["user"]["id"] == "account:me"

            self.app.patch_json(
                "/accounts/me",
                {"data": {"password": "blah"}},
                status=200,
                headers=get_user_headers("me", "bouh"),
            )

            resp = self.app.get("/", headers=get_user_headers("me", "blah"))
            assert resp.json["user"]["id"] == "account:me"

            assert mocked_bcrypt.checkpw.call_count == 2

    def test_authentication_refresh_the_cache_each_time_we_authenticate(self):
        hmac_secret = self.app.app.registry.settings["userid_hmac_secret"]
        cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_CACHE_KEY.format("me"))

        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bouh"}}, status=201)
        resp = self.app.get("/", headers=get_user_headers("me", "bouh"))
        assert resp.json["user"]["id"] == "account:me"

        self.app.app.registry.cache.expire(cache_key, 10)

        resp = self.app.get("/", headers=get_user_headers("me", "bouh"))
        assert resp.json["user"]["id"] == "account:me"

        assert self.app.app.registry.cache.ttl(cache_key) >= 20

        resp = self.app.get("/", headers=get_user_headers("me", "blah"))
        assert "user" not in resp.json

    def test_validate_view_not_active(self):
        # The `validate` view is only active when the `account_validation` option is enabled.
        # Create the user.
        self.app.post_json(
            "/accounts", {"data": {"id": "alice@example.com", "password": "12éé6"}}, status=201
        )
        # Validate the user.
        self.app.post_json("/accounts/alice@example.com/validate/some_validation_key", status=404)

    def test_reset_password_view_not_active(self):
        # The `validate` view is only active when the `account_validation` option is enabled.
        # Create the user.
        self.app.post_json(
            "/accounts", {"data": {"id": "alice@example.com", "password": "12éé6"}}, status=201
        )
        # Ask for a reset password.
        self.app.post_json("/accounts/alice@example.com/reset-password", status=404)


class AccountValidationCreationTest(AccountsValidationWebTest):
    def test_create_account_fails_if_not_email(self):
        resp = self.app.post_json(
            "/accounts", {"data": {"id": "alice", "password": "12éé6"}}, status=400
        )
        assert "user id should match" in resp.json["message"]

    def test_create_account_stores_activated_field(self):
        uuid_string = "20e81ab7-51c0-444f-b204-f1c4cfe1aa7a"
        with mock.patch("uuid.uuid4", return_value=uuid.UUID(uuid_string)):
            resp = self.app.post_json(
                "/accounts",
                {
                    "data": {
                        "id": "alice@example.com",
                        "password": "12éé6",
                        "email-context": {
                            "name": "Alice",
                            "activation-form-url": "https://example.com",
                        },
                    }
                },
                status=201,
            )
        assert "activation-key" not in resp.json["data"]
        assert "validated" in resp.json["data"]
        assert not resp.json["data"]["validated"]
        assert len(self.mailer.outbox) == 1
        mail = self.mailer.outbox[0]  # Get the validation email.
        assert mail.sender == "admin@example.com"
        assert mail.subject == "Alice, activate your account alice@example.com"
        assert mail.recipients == ["alice@example.com"]
        # The {{bad-key}} from the template will be rendered as {bad-key} in
        # the final email, instead of failing the formatting.
        assert mail.body == f"https://example.com/alice@example.com/{uuid_string} {{bad-key}}"
        # The activation key is stored in the cache.
        assert get_cached_validation_key("alice@example.com", self.app.app.registry) == uuid_string

    def test_cant_authenticate_with_unactivated_account(self):
        self.app.post_json(
            "/accounts",
            {"data": {"id": "alice@example.com", "password": "12éé6", "activated": False}},
            status=201,
        )
        resp = self.app.get("/", headers=get_user_headers("alice@example.com", "12éé6"))
        assert "user" not in resp.json

    def test_validation_fail_bad_user(self):
        # Validation should fail on a non existing user.
        resp = self.app.post_json("/accounts/alice@example.com/validate/123", {}, status=403)
        assert "Account ID and activation key do not match" in resp.json["message"]

    def test_validation_fail_bad_activation_key(self):
        uuid_string = "20e81ab7-51c0-444f-b204-f1c4cfe1aa7a"
        with mock.patch("uuid.uuid4", return_value=uuid.UUID(uuid_string)):
            self.app.post_json(
                "/accounts", {"data": {"id": "alice@example.com", "password": "12éé6"}}, status=201
            )
        # Validate the user.
        resp = self.app.post_json(
            "/accounts/alice@example.com/validate/bad-activation-key", {}, status=403
        )
        assert "Account ID and activation key do not match" in resp.json["message"]
        # The activation key is still in the cache
        assert get_cached_validation_key("alice@example.com", self.app.app.registry) is not None

    def test_validation_validates_user(self):
        # On user activation the 'validated' field is set to True.
        uuid_string = "20e81ab7-51c0-444f-b204-f1c4cfe1aa7a"
        with mock.patch("uuid.uuid4", return_value=uuid.UUID(uuid_string)):
            self.app.post_json(
                "/accounts",
                {
                    "data": {
                        "id": "alice@example.com",
                        "password": "12éé6",
                        "email-context": {"name": "Alice", "homepage": "https://example.com"},
                    }
                },
                status=201,
            )
        resp = self.app.post_json(
            "/accounts/alice@example.com/validate/" + uuid_string, {}, status=200
        )
        assert "validated" in resp.json
        assert resp.json["validated"]
        # An active user can authenticate.
        resp = self.app.get("/", headers=get_user_headers("alice@example.com", "12éé6"))
        assert resp.json["user"]["id"] == "account:alice@example.com"
        # Once activated, the activation key is removed from the cache.
        assert get_cached_validation_key("alice@example.com", self.app.app.registry) is None
        assert len(self.mailer.outbox) == 2  # Validation email, reset password email.
        mail = self.mailer.outbox[1]  # Get the confirmation email.
        assert mail.sender == "admin@example.com"
        assert mail.subject == "Alice, your account alice@example.com is now active"
        assert mail.recipients == ["alice@example.com"]
        assert (
            mail.body
            == "Your account alice@example.com has been successfully activated. Connect to https://example.com"
        )

    def test_previously_created_accounts_can_still_authenticate(self):
        """Accounts created before activating the 'account validation' option can still authenticate."""
        # Create an account without going through the accounts API.
        hashed_password = hash_password("12éé6")
        self.app.app.registry.storage.create(
            parent_id="alice",
            resource_name="account",
            record={"id": "alice", "password": hashed_password},
        )
        resp = self.app.get("/", headers=get_user_headers("alice", "12éé6"))
        assert resp.json["user"]["id"] == "account:alice"

    def test_reset_password_bad_user(self):
        resp = self.app.post_json("/accounts/alice@example.com/reset-password", {}, status=200)
        # Don't give information on the existence of a user id: return a generic message.
        assert resp.json["message"] == "A temporary reset password has been sent by mail"
        # Make sure no email was sent.
        assert len(self.mailer.outbox) == 0

    def test_reset_password_bad_email(self):
        # Create an account without going through the accounts API.
        hashed_password = hash_password("12éé6")
        self.app.app.registry.storage.create(
            parent_id="alice",
            resource_name="account",
            record={"id": "alice", "password": hashed_password},
        )
        resp = self.app.post_json("/accounts/alice/reset-password", {}, status=400)
        assert "user id should match" in resp.json["message"]

    def test_reset_password_sends_email(self):
        reset_password = "20e81ab7-51c0-444f-b204-f1c4cfe1aa7a"
        with mock.patch("uuid.uuid4", return_value=uuid.UUID(reset_password)):
            # Create the user.
            self.app.post_json(
                "/accounts", {"data": {"id": "alice@example.com", "password": "12éé6"}}, status=201
            )
            # Ask for a reset password.
            resp = self.app.post_json(
                "/accounts/alice@example.com/reset-password",
                {"data": {"email-context": {"name": "Alice"}}},
                status=200,
            )
        assert resp.json["message"] == "A temporary reset password has been sent by mail"
        assert len(self.mailer.outbox) == 2  # Validation email, reset password email.
        mail = self.mailer.outbox[1]  # Get the reset password email
        assert mail.sender == "admin@example.com"
        assert mail.subject == "Alice, here is a temporary reset password for alice@example.com"
        assert (
            mail.body
            == f"You can use this temporary reset password {reset_password} to change your account alice@example.com password"
        )
        # The reset password is stored in the cache.
        cached_password = get_cached_reset_password(
            "alice@example.com", self.app.app.registry
        ).encode(encoding="utf-8")
        pwd_str = reset_password.encode(encoding="utf-8")
        assert bcrypt.checkpw(pwd_str, cached_password)

    def test_fail_use_reset_password_bad_data(self):
        validation_key = reset_password = "20e81ab7-51c0-444f-b204-f1c4cfe1aa7a"
        with mock.patch("uuid.uuid4", return_value=uuid.UUID(reset_password)):
            # Create the user.
            self.app.post_json(
                "/accounts", {"data": {"id": "alice@example.com", "password": "12éé6"}}, status=201
            )
            # Validate the user.
            resp = self.app.post_json(
                "/accounts/alice@example.com/validate/" + validation_key, status=200
            )
            # Ask for a reset password.
            self.app.post_json("/accounts/alice@example.com/reset-password", status=200)
        # Using reset password needs data.
        self.app.put_json(
            "/accounts/alice@example.com",
            headers=get_user_headers("alice@example.com", reset_password),
            status=401,
        )
        # Using reset password needs password field.
        self.app.put_json(
            "/accounts/alice@example.com",
            {"data": {"foo": "bar"}},
            headers=get_user_headers("alice@example.com", reset_password),
            status=401,
        )
        # Using reset password accepts only password field.
        self.app.put_json(
            "/accounts/alice@example.com",
            {"data": {"password": "newpass", "foo": "bar"}},
            headers=get_user_headers("alice@example.com", reset_password),
            status=401,
        )
        # Using wrong reset password fails.
        self.app.put_json(
            "/accounts/alice@example.com",
            {"data": {"password": "newpass"}},
            headers=get_user_headers("alice@example.com", "some random password"),
            status=401,
        )
        # Can't use the reset password to modify other resources than accounts.
        resp = self.app.post_json(
            "/buckets/default/collections",
            {"data": {"id": "some_collection_id"}},
            headers=get_user_headers("alice@example.com", reset_password),
            status=401,
        )
        assert resp.json["message"] == "Please authenticate yourself to use this endpoint."
        # Can't use reset password to authenticate.
        resp = self.app.get("/", headers=get_user_headers("alice@example.com", reset_password))
        assert "user" not in resp.json

    def test_use_reset_password_to_change_password(self):
        validation_key = reset_password = "20e81ab7-51c0-444f-b204-f1c4cfe1aa7a"
        with mock.patch("uuid.uuid4", return_value=uuid.UUID(reset_password)):
            # Create the user.
            self.app.post_json(
                "/accounts", {"data": {"id": "alice@example.com", "password": "12éé6"}}, status=201
            )
            # Validate the user.
            resp = self.app.post_json(
                "/accounts/alice@example.com/validate/" + validation_key, {}, status=200
            )
            # Ask for a reset password.
            self.app.post_json("/accounts/alice@example.com/reset-password", {}, status=200)
        # Use reset password to set a new password.
        self.app.patch_json(
            "/accounts/alice@example.com",
            {"data": {"password": "newpass"}},
            headers=get_user_headers("alice@example.com", reset_password),
            status=200,
        )
        # Can use the new password to authenticate.
        resp = self.app.get("/", headers=get_user_headers("alice@example.com", "newpass"))
        assert resp.json["user"]["id"] == "account:alice@example.com"
        # The user hasn't changed.
        resp = self.app.get(
            "/accounts/alice@example.com", headers=get_user_headers("alice@example.com", "newpass")
        )
        assert resp.json["data"]["id"] == "alice@example.com"
        assert resp.json["data"]["validated"]
        # The reset password isn't in the cache anymore
        assert get_cached_reset_password("alice@example.com", self.app.app.registry) is None
        # Can't use the reset password anymore to authenticate.
        resp = self.app.get("/", headers=get_user_headers("alice@example.com", reset_password))
        assert "user" not in resp.json

    def test_user_creation_listener(self):
        request = DummyRequest()
        impacted_object = {"new": {"id": "alice", "password": "12éé6"}}
        with mock.patch("kinto.plugins.accounts.mails.Emailer.send_mail") as mocked_send_mail:
            # No email sent if account validation is not enabled.
            event = ResourceChanged({"action": ACTIONS.UPDATE.value}, [impacted_object], request)
            on_account_created(event)
            mocked_send_mail.assert_not_called()
            # No email sent if there's no activation key in the cache.
            request.registry.settings["account_validation"] = True
            event = ResourceChanged({"action": ACTIONS.UPDATE.value}, [impacted_object], request)
            request.registry.cache.get = mock.MagicMock(return_value=None)
            on_account_created(event)
            mocked_send_mail.assert_not_called()
            # Email sent if there is an activation key in the cache.
            request.registry.cache.get = mock.MagicMock(return_value="some activation key")
            on_account_created(event)
            mocked_send_mail.assert_called_once()

    def test_user_validation_listener(self):
        request = DummyRequest()
        old_inactive = {"id": "alice", "password": "12éé6", "validated": False}
        old_active = {"id": "alice", "password": "12éé6", "validated": True}
        new_inactive = {"id": "alice", "password": "12éé6", "validated": False}
        new_active = {"id": "alice", "password": "12éé6", "validated": True}
        with mock.patch("kinto.plugins.accounts.mails.Emailer.send_mail") as mocked_send_mail:
            # No email sent if account validation is not enabled.
            event = ResourceChanged(
                {"action": ACTIONS.UPDATE.value},
                [{"old": old_inactive, "new": new_inactive}],
                request,
            )
            on_account_activated(event)
            mocked_send_mail.assert_not_called()
            # No email sent if the old account was already active.
            request.registry.settings["account_validation"] = True
            event = ResourceChanged(
                {"action": ACTIONS.UPDATE.value}, [{"old": old_active, "new": new_active}], request
            )
            request.registry.cache.get = mock.MagicMock(return_value=None)
            on_account_activated(event)
            mocked_send_mail.assert_not_called()
            # No email sent if the new account is still inactive.
            event = ResourceChanged(
                {"action": ACTIONS.UPDATE.value},
                [{"old": old_inactive, "new": new_inactive}],
                request,
            )
            request.registry.cache.get = mock.MagicMock(return_value=None)
            on_account_activated(event)
            mocked_send_mail.assert_not_called()
            # Email sent if there is an activation key in the cache.
            event = ResourceChanged(
                {"action": ACTIONS.UPDATE.value},
                [{"old": old_inactive, "new": new_active}],
                request,
            )
            on_account_activated(event)
            mocked_send_mail.assert_called_once()


class AccountUpdateTest(AccountsWebTest):
    def setUp(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "123456"}}, status=201)

    def test_password_can_be_changed(self):
        self.app.put_json(
            "/accounts/alice",
            {"data": {"password": "bouh"}},
            headers=get_user_headers("alice", "123456"),
            status=200,
        )

    def test_authentication_with_old_password_is_denied_after_change(self):
        self.app.put_json(
            "/accounts/alice",
            {"data": {"password": "bouh"}},
            headers=get_user_headers("alice", "123456"),
            status=200,
        )
        self.app.get("/accounts/alice", headers=get_user_headers("alice", "123456"), status=401)

    def test_authentication_with_new_password_is_accepted_after_change(self):
        self.app.put_json(
            "/accounts/alice",
            {"data": {"password": "bouh"}},
            headers=get_user_headers("alice", "123456"),
            status=200,
        )
        self.app.get("/accounts/alice", headers=get_user_headers("alice", "bouh"))

    def test_username_and_account_id_must_match(self):
        resp = self.app.patch_json(
            "/accounts/alice",
            {"data": {"id": "bob", "password": "bouh"}},
            headers=get_user_headers("alice", "123456"),
            status=400,
        )
        assert "does not match" in resp.json["message"]

    def test_cannot_patch_unknown_account(self):
        self.app.patch_json(
            "/accounts/bob",
            {"data": {"password": "bouh"}},
            headers=get_user_headers("alice", "123456"),
            status=403,
        )

    def test_cannot_patch_someone_else_account(self):
        self.app.put_json("/accounts/bob", {"data": {"password": "bob"}}, status=201)
        self.app.patch_json(
            "/accounts/bob",
            {"data": {"password": "bouh"}},
            headers=get_user_headers("alice", "123456"),
            status=403,
        )

    def test_metadata_can_be_changed(self):
        resp = self.app.patch_json(
            "/accounts/alice",
            {"data": {"age": "captain"}},
            headers=get_user_headers("alice", "123456"),
        )
        assert resp.json["data"]["age"] == "captain"

    def test_changing_metadata_does_not_change_password(self):
        headers = get_user_headers("alice", "123456")
        url = "/accounts/alice"
        resp = self.app.get(url, headers=headers)
        before = resp.json["data"]["password"]

        self.app.patch_json(url, {"data": {"age": "captain"}}, headers=headers)

        resp = self.app.get(url, headers=headers)
        after = resp.json["data"]["password"]
        assert before == after


class AccountDeleteTest(AccountsWebTest):
    def setUp(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "123456"}}, status=201)

    def test_account_can_be_deleted(self):
        self.app.delete("/accounts/alice", headers=get_user_headers("alice", "123456"))

    def test_authentication_is_denied_after_delete(self):
        self.app.delete("/accounts/alice", headers=get_user_headers("alice", "123456"))
        self.app.get("/accounts/alice", headers=get_user_headers("alice", "123456"), status=401)


class AccountViewsTest(AccountsWebTest):
    def setUp(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "123456"}}, status=201)
        self.app.put_json("/accounts/bob", {"data": {"password": "azerty"}}, status=201)

    def test_account_list_is_forbidden_if_anonymous(self):
        self.app.get("/accounts", status=401)

    def test_account_detail_is_forbidden_if_anonymous(self):
        self.app.get("/accounts/alice", status=401)

    def test_accounts_list_contains_only_one_record(self):
        resp = self.app.get("/accounts", headers=get_user_headers("alice", "123456"))
        assert len(resp.json["data"]) == 1

    def test_account_record_can_be_obtained_if_authenticated(self):
        self.app.get("/accounts/alice", headers=get_user_headers("alice", "123456"))

    def test_cannot_obtain_someone_else_account(self):
        self.app.get("/accounts/bob", headers=get_user_headers("alice", "123456"), status=403)

    def test_cannot_obtain_unknown_account(self):
        self.app.get("/accounts/jeanine", headers=get_user_headers("alice", "123456"), status=403)


class PermissionsEndpointTest(AccountsWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["experimental_permissions_endpoint"] = "True"
        return settings

    def setUp(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "123456"}}, status=201)
        self.headers = get_user_headers("alice", "123456")
        self.app.put("/buckets/a", headers=self.headers)
        self.app.put("/buckets/a/collections/b", headers=self.headers)
        self.app.put("/buckets/a/collections/b/records/c", headers=self.headers)

    def test_permissions_endpoint_is_compatible_with_accounts_plugin(self):
        resp = self.app.get("/permissions", headers=self.headers)
        uris = [r["uri"] for r in resp.json["data"]]
        assert uris == [
            "/buckets/a/collections/b/records/c",
            "/buckets/a/collections/b",
            "/buckets/a",
            "/accounts/alice",
            "/",
        ]

    def test_account_create_read_write_permissions_(self):
        resp = self.app.get("/permissions", headers=self.headers)
        buckets = resp.json["data"]
        account = buckets[3]
        account["permissions"].sort()
        root = buckets[4]
        root["permissions"].sort()
        self.assertEqual(
            account,
            {
                "account_id": "alice",
                "id": "alice",
                "permissions": ["read", "write"],
                "resource_name": "account",
                "uri": "/accounts/alice",
            },
        )
        self.assertEqual(
            root,
            {
                "permissions": ["account:create", "bucket:create"],
                "resource_name": "root",
                "uri": "/",
            },
        )


class PermissionsEndpointTestUnauthenticatedCreatePermission(AccountsWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["experimental_permissions_endpoint"] = "True"
        settings["bucket_create_principals"] = "system.Everyone"
        return settings

    def setUp(self):
        self.everyone_headers = get_user_headers("")

    def test_permissions_endpoint_is_compatible_with_accounts_plugin(self):
        resp = self.app.get("/permissions", headers=self.everyone_headers)
        buckets = resp.json["data"]
        root = buckets[0]
        root["permissions"].sort()
        self.assertEqual(
            root,
            {
                "permissions": ["account:create", "bucket:create"],
                "resource_name": "root",
                "uri": "/",
            },
        )


class AdminTest(AccountsWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["account_write_principals"] = "account:admin"
        settings["account_read_principals"] = "account:admin"
        return settings

    def setUp(self):
        self.app.put_json("/accounts/admin", {"data": {"password": "123456"}}, status=201)
        self.admin_headers = get_user_headers("admin", "123456")

        self.app.put_json("/accounts/bob", {"data": {"password": "987654"}}, status=201)

    def test_admin_can_get_other_accounts(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "azerty"}}, status=201)

        resp = self.app.get("/accounts/alice", headers=get_user_headers("alice", "azerty"))
        assert resp.json["data"]["id"] == "alice"

    def test_admin_can_delete_other_accounts(self):
        self.app.delete_json("/accounts/bob", headers=self.admin_headers)
        self.app.get("/accounts/bob", headers=get_user_headers("bob", "987654"), status=401)

    def test_admin_can_delete_all_accounts(self):
        self.app.delete_json("/accounts", headers=self.admin_headers)

        self.app.get("/accounts/bob", headers=get_user_headers("bob", "987654"), status=401)

    def test_admin_can_set_others_password(self):
        self.app.patch_json(
            "/accounts/bob", {"data": {"password": "bouh"}}, headers=self.admin_headers
        )
        self.app.get("/accounts/bob", headers=get_user_headers("bob", "987654"), status=401)
        self.app.get("/accounts/bob", headers=get_user_headers("bob", "bouh"))

    def test_admin_can_retrieve_accounts_list(self):
        self.app.put_json("/accounts/alice", {"data": {"password": "azerty"}}, status=201)

        resp = self.app.get("/accounts", headers=self.admin_headers)
        usernames = [r["id"] for r in resp.json["data"]]
        assert sorted(usernames) == ["admin", "alice", "bob"]

    def test_user_created_by_admin_with_put_can_see_her_record(self):
        self.app.put_json(
            "/accounts/alice", {"data": {"password": "bouh"}}, headers=self.admin_headers
        )

        resp = self.app.get("/accounts/alice", headers=get_user_headers("alice", "bouh"))
        assert resp.json["permissions"] == {"write": ["account:alice"]}

    def test_user_created_by_admin_with_post_can_see_her_record(self):
        self.app.post_json(
            "/accounts", {"data": {"id": "alice", "password": "bouh"}}, headers=self.admin_headers
        )

        resp = self.app.get("/accounts/alice", headers=get_user_headers("alice", "bouh"))
        assert resp.json["permissions"] == {"write": ["account:alice"]}

    def test_user_created_by_admin_can_delete_her_record(self):
        self.app.post_json(
            "/accounts", {"data": {"id": "alice", "password": "bouh"}}, headers=self.admin_headers
        )

        self.app.delete("/accounts/alice", headers=get_user_headers("alice", "bouh"))


class CheckAdminCreateTest(AccountsWebTest):
    def test_raise_if_create_but_no_write(self):
        with self.assertRaises(ConfigurationError):
            self.make_app({"account_create_principals": "account:admin"})


class CreateOtherUserTest(AccountsWebTest):
    def setUp(self):
        self.app.put_json("/accounts/bob", {"data": {"password": "123456"}}, status=201)
        self.bob_headers = get_user_headers("bob", "123456")

    def test_create_other_id_is_still_required(self):
        self.app.post_json(
            "/accounts", {"data": {"password": "azerty"}}, status=400, headers=self.bob_headers
        )

    def test_create_other_forbidden_without_write(self):
        self.app.put_json(
            "/accounts/alice",
            {"data": {"password": "azerty"}},
            status=400,
            headers=self.bob_headers,
        )


class WithBasicAuthTest(AccountsWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {"multiauth.policies": "account basicauth"}
        return super().get_app_settings(extras)

    def test_password_field_is_mandatory(self):
        self.app.post_json("/accounts", {"data": {"id": "me"}}, status=400)

    def test_id_field_is_mandatory(self):
        self.app.post_json("/accounts", {"data": {"password": "pass"}}, status=400)

    def test_fallsback_on_basicauth(self):
        self.app.post_json("/accounts", {"data": {"id": "me", "password": "bleh"}})

        resp = self.app.get("/", headers=get_user_headers("me", "wrong"))
        assert "basicauth" in resp.json["user"]["id"]

        resp = self.app.get("/", headers=get_user_headers("me", "bleh"))
        assert "account" in resp.json["user"]["id"]

    def test_raise_configuration_if_wrong_error(self):
        with self.assertRaises(ConfigurationError):
            self.make_app({"multiauth.policies": "basicauth account"})


class CreateUserTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()
        self.registry.settings = {"includes": "kinto.plugins.accounts"}

    def test_create_user_in_read_only_displays_an_error(self):
        with mock.patch("kinto.plugins.accounts.scripts.logger") as mocked:
            self.registry.settings["readonly"] = "true"
            code = scripts.create_user({"registry": self.registry})
            assert code == 51
            mocked.error.assert_called_once_with("Cannot create a user with " "a readonly server.")

    def test_create_user_when_not_included_displays_an_error(self):
        with mock.patch("kinto.plugins.accounts.scripts.logger") as mocked:
            self.registry.settings["includes"] = ""
            code = scripts.create_user({"registry": self.registry})
            assert code == 52
            mocked.error.assert_called_once_with(
                "Cannot create a user when the accounts " "plugin is not installed."
            )

    def test_create_user_with_an_invalid_username_and_password_confirmation_recovers(self):
        with mock.patch("kinto.plugins.accounts.scripts.input", side_effect=["&zert", "username"]):
            with mock.patch(
                "kinto.plugins.accounts.scripts.getpass.getpass",
                side_effect=["password", "p4ssw0rd", "password", "password"],
            ):
                code = scripts.create_user({"registry": self.registry}, None, None)
                assert self.registry.storage.update.call_count == 1
                self.registry.permission.add_principal_to_ace.assert_called_with(
                    "/accounts/username", "write", "account:username"
                )
                assert code == 0

    def test_create_user_with_a_valid_username_and_password_confirmation(self):
        with mock.patch("kinto.plugins.accounts.scripts.input", return_value="username"):
            with mock.patch(
                "kinto.plugins.accounts.scripts.getpass.getpass", return_value="password"
            ):
                code = scripts.create_user({"registry": self.registry})
                assert self.registry.storage.update.call_count == 1
                self.registry.permission.add_principal_to_ace.assert_called_with(
                    "/accounts/username", "write", "account:username"
                )
                assert code == 0

    def test_create_user_with_valid_username_and_password_parameters(self):
        code = scripts.create_user({"registry": self.registry}, "username", "password")
        assert self.registry.storage.update.call_count == 1
        self.registry.permission.add_principal_to_ace.assert_called_with(
            "/accounts/username", "write", "account:username"
        )
        assert code == 0

    def test_create_user_aborted_by_eof(self):
        with mock.patch("kinto.plugins.accounts.scripts.input", side_effect=EOFError):
            code = scripts.create_user({"registry": self.registry})
            assert code == 53
