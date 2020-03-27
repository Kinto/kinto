import re
import uuid

import colander
from pyramid import httpexceptions
from pyramid.decorator import reify
from pyramid.events import subscriber
from pyramid.security import Authenticated, Everyone
from pyramid.settings import aslist

from kinto.core import resource
from kinto.core.errors import http_error, raise_invalid
from kinto.core.events import ACTIONS, ResourceChanged
from kinto.views import NameGenerator

from ..mails import Emailer
from ..utils import (
    ACCOUNT_POLICY_NAME,
    cache_validation_key,
    delete_cached_account,
    get_cached_validation_key,
    hash_password,
)

DEFAULT_EMAIL_REGEXP = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"


def _extract_posted_body_id(request):
    try:
        # Anonymous creation with POST.
        return request.json["data"]["id"]
    except (ValueError, KeyError):
        # Bad POST data.
        if request.method.lower() == "post":
            error_details = {"name": "data.id", "description": "data.id in body: Required"}
            raise_invalid(request, **error_details)
        # Anonymous GET
        error_msg = "Cannot read accounts."
        raise http_error(httpexceptions.HTTPUnauthorized(), error=error_msg)


class AccountIdGenerator(NameGenerator):
    """Allow @ signs in account IDs."""

    regexp = r"^[a-zA-Z0-9][+.@a-zA-Z0-9_-]*$"


class AccountSchema(resource.ResourceSchema):
    password = colander.SchemaNode(colander.String())


@resource.register()
class Account(resource.Resource):

    schema = AccountSchema

    def __init__(self, request, context):
        settings = request.registry.settings
        # Store if current user is administrator (before accessing get_parent_id())
        allowed_from_settings = settings.get("account_write_principals", [])
        context.is_administrator = (
            len(set(aslist(allowed_from_settings)) & set(request.prefixed_principals)) > 0
        )
        # Shortcut to check if current is anonymous (before get_parent_id()).
        context.is_anonymous = Authenticated not in request.effective_principals
        # Is the "accounts validation" setting set?
        context.validation_enabled = settings.get("account_validation", False)
        # Account validation requires the user id to be an email.
        validation_email_regexp = settings.get(
            "account_validation.email_regexp", DEFAULT_EMAIL_REGEXP
        )
        context.validation_email_regexp = re.compile(validation_email_regexp)

        super().__init__(request, context)

        # Overwrite the current principal set by Resource.
        if self.model.current_principal == Everyone or context.is_administrator:
            # Creation is anonymous, but author with write perm is this:
            self.model.current_principal = f"{ACCOUNT_POLICY_NAME}:{self.model.parent_id}"

    @reify
    def id_generator(self):
        # This generator is used for ID validation.
        return AccountIdGenerator()

    def get_parent_id(self, request):
        # The whole challenge here is that we want to isolate what
        # authenticated users can list, but give access to everything to
        # administrators.
        # Plus when anonymous create accounts, we have to set their parent id
        # to the same value they would obtain when authenticated.
        if self.context.is_administrator:
            if self.context.on_plural_endpoint:
                # Accounts created by admin should have userid as parent.
                if request.method.lower() == "post":
                    return _extract_posted_body_id(request)
                else:
                    # Admin see all accounts.
                    return "*"
            else:
                # No pattern matching for admin on single record.
                return request.matchdict["id"]

        if not self.context.is_anonymous:
            # Authenticated users see their own account only.
            return request.selected_userid

        # Anonymous creation with PUT.
        if "id" in request.matchdict:
            return request.matchdict["id"]

        return _extract_posted_body_id(request)

    def process_object(self, new, old=None):
        new = super(Account, self).process_object(new, old)

        if "data" in self.request.json and "password" in self.request.json["data"]:
            new["password"] = hash_password(new["password"])

        # Do not let accounts be created without usernames.
        if self.model.id_field not in new:
            error_details = {"name": "data.id", "description": "Accounts must have an ID."}
            raise_invalid(self.request, **error_details)

        # Account validation requires that the record ID is an email address.
        # TODO: this might be better suited for a schema. Do we have a way to
        # dynamically change the schema according to the settings?
        if self.context.validation_enabled and old is None:
            email_regexp = self.context.validation_email_regexp
            # Account validation requires that the record ID is an email address.
            user_email = new[self.model.id_field]
            if not email_regexp.match(user_email):
                error_details = {
                    "name": "data.id",
                    "description": f"Account validation is enabled, and user id should match {email_regexp}",
                }
                raise_invalid(self.request, **error_details)

            activation_key = str(uuid.uuid4())
            new["validated"] = False

            # Store the activation key in the cache to be used in the `validate` endpoint.
            cache_validation_key(activation_key, new["id"], self.request.registry)

        # Administrators can reach other accounts and anonymous have no
        # selected_userid. So do not try to enforce.
        if self.context.is_administrator or self.context.is_anonymous:
            return new

        # Otherwise, we force the id to match the authenticated username.
        if new[self.model.id_field] != self.request.selected_userid:
            error_details = {
                "name": "data.id",
                "description": "Username and account ID do not match.",
            }
            raise_invalid(self.request, **error_details)

        return new


# Clear cache on account change
@subscriber(
    ResourceChanged, for_resources=("account",), for_actions=(ACTIONS.UPDATE, ACTIONS.DELETE)
)
def on_account_changed(event):
    request = event.request

    for obj in event.impacted_objects:
        # Extract username and password from current user
        username = obj["old"]["id"]
        # Delete cache
        delete_cached_account(username, request.registry)


# Send activation code by email on account creation if account validation is enabled.
@subscriber(ResourceChanged, for_resources=("account",), for_actions=(ACTIONS.CREATE,))
def on_account_created(event):
    request = event.request
    settings = request.registry.settings
    if not settings.get("account_validation", False):
        return

    for impacted_object in event.impacted_objects:
        account = impacted_object["new"]
        user_email = account["id"]
        activation_key = get_cached_validation_key(user_email, request.registry)
        if activation_key is None:
            continue

        # Send an email to the user with the link to activate their account.
        Emailer(request, account).send_activation(activation_key)
