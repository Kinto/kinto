import re
import uuid

from pyramid import httpexceptions
from pyramid.events import subscriber

from kinto.core import Service
from kinto.core.errors import http_error, raise_invalid
from kinto.core.events import ACTIONS, ResourceChanged
from kinto.core.storage import exceptions as storage_exceptions

from ..mails import Emailer
from ..utils import (
    cache_reset_password,
    delete_cached_validation_key,
    get_cached_validation_key,
    hash_password,
)
from . import DEFAULT_EMAIL_REGEXP

# Account validation (enable in the settings).
validation = Service(
    name="account-validation",
    path="/accounts/{user_id}/validate/{activation_key}",
    description="Validate an account",
)


def check_validation_key(activation_key, username, registry):
    """Given a username, compare the activation-key provided with the one from the cache."""
    cache_result = get_cached_validation_key(username, registry)

    if cache_result == activation_key:
        delete_cached_validation_key(username, registry)  # We're done with the activation key.
        return True
    return False


@validation.post()
def post_validation(request):
    user_id = request.matchdict["user_id"]
    activation_key = request.matchdict["activation_key"]

    parent_id = user_id
    try:
        user = request.registry.storage.get(
            parent_id=parent_id, resource_name="account", object_id=user_id
        )
    except storage_exceptions.ObjectNotFoundError:
        # Don't give information on the existence of a user id: return a generic error message.
        error_details = {"message": "Account ID and activation key do not match"}
        raise http_error(httpexceptions.HTTPForbidden(), **error_details)

    if not check_validation_key(activation_key, user_id, request.registry):
        error_details = {"message": "Account ID and activation key do not match"}
        raise http_error(httpexceptions.HTTPForbidden(), **error_details)

    # User is now validated.
    new = user.copy()
    new["validated"] = True

    result = request.registry.storage.update(
        parent_id=parent_id, resource_name="account", object_id=user_id, obj=new
    )
    request.notify_resource_event(
        parent_id=parent_id,
        timestamp=result["last_modified"],
        data=result,
        action=ACTIONS.UPDATE,
        old=user,
        resource_name="account",
    )
    return new


# Password reset.
reset_password = Service(
    name="reset-password",
    path="/accounts/{user_id}/reset-password",
    description="Send a temporary reset password by mail for an account",
)


@reset_password.post()
def post_reset_password(request):
    user_id = request.matchdict["user_id"]

    parent_id = user_id
    try:
        user = request.registry.storage.get(
            parent_id=parent_id, resource_name="account", object_id=user_id
        )
    except storage_exceptions.ObjectNotFoundError:
        # Don't give information on the existence of a user id: return a generic message.
        return {"message": "A temporary reset password has been sent by mail"}

    settings = request.registry.settings

    user_email = user["id"]
    email_regexp = settings.get("account_validation.email_regexp", DEFAULT_EMAIL_REGEXP)
    compiled_email_regexp = re.compile(email_regexp)
    if not compiled_email_regexp.match(user_email):
        error_details = {
            "name": "data.id",
            "description": f"The user id should match {email_regexp}.",
        }
        raise_invalid(request, **error_details)

    reset_password = str(uuid.uuid4())
    hashed_reset_password = hash_password(reset_password)
    cache_reset_password(hashed_reset_password, user_id, request.registry)

    # Send a temporary reset password by mail.
    Emailer(request, user).send_temporary_reset_password(reset_password)

    return {"message": "A temporary reset password has been sent by mail"}


# Send confirmation email on account activation if account validation is enabled.
@subscriber(ResourceChanged, for_resources=("account",), for_actions=(ACTIONS.UPDATE,))
def on_account_activated(event):
    request = event.request
    settings = request.registry.settings
    if not settings.get("account_validation", False):
        return

    for impacted_object in event.impacted_objects:
        old_account = impacted_object["old"]
        account = impacted_object["new"]
        if old_account.get("validated", True) or not account.get("validated", False):
            # It's not an account activation, bail.
            continue

        # Send a confirmation email.
        Emailer(request, account).send_confirmation()
