import re
import uuid
from pyramid import httpexceptions
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message


from kinto.core import Service, utils
from kinto.core.errors import raise_invalid, http_error
from kinto.core.storage import exceptions as storage_exceptions

from ..utils import (
    hash_password,
    is_validated,
    EmailFormatter,
    ACCOUNT_RESET_PASSWORD_CACHE_KEY,
    ACCOUNT_VALIDATION_CACHE_KEY,
)


# Account validation (enable in the settings).
validation = Service(
    name="account-validation",
    path="/accounts/{user_id}/validate/{activation_key}",
    description="Validate an account",
)


def check_validation_key(activation_key, username, registry):
    """Given a username, compare the activation-key provided with the one from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_VALIDATION_CACHE_KEY.format(username))

    cache = registry.cache
    cache_result = cache.get(cache_key)

    if cache_result == activation_key:
        cache.delete(cache_key)  # We're done with the activation key.
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

    if is_validated(user):
        error_details = {"message": f"Account {user_id} has already been validated"}
        raise http_error(httpexceptions.HTTPForbidden(), **error_details)

    if not check_validation_key(activation_key, user_id, request.registry):
        error_details = {"message": "Account ID and activation key do not match"}
        raise http_error(httpexceptions.HTTPForbidden(), **error_details)

    # User is now validated.
    user["validated"] = True

    request.registry.storage.update(
        parent_id=parent_id, resource_name="account", object_id=user_id, record=user
    )

    # Send a confirmation email.
    settings = request.registry.settings
    email_confirmation_subject_template = settings.get(
        "account_validation.email_confirmation_subject_template", "Account active"
    )
    email_confirmation_body_template = settings.get(
        "account_validation.email_confirmation_body_template", "The account {id} is now active"
    )
    email_sender = settings.get("account_validation.email_sender", "admin@example.com")

    user_email = user["id"]
    mailer = get_mailer(request)
    email_context = user.get("email-context", {})

    formatter = EmailFormatter()
    formatted_subject = formatter.format(
        email_confirmation_subject_template, **user, **email_context
    )
    formatted_body = formatter.format(email_confirmation_body_template, **user, **email_context)

    message = Message(
        subject=formatted_subject,
        sender=email_sender,
        recipients=[user_email],
        body=formatted_body,
    )
    mailer.send(message)

    return user


# Password reset.
reset_password = Service(
    name="reset-password",
    path="/accounts/{user_id}/reset-password",
    description="Send a temporary reset password by mail for an account",
)


def cache_reset_password(reset_password, username, registry):
    """Store a reset-password in the cache."""
    settings = registry.settings
    hmac_secret = settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_RESET_PASSWORD_CACHE_KEY.format(username))
    # Store a reset password for 7 days by default.
    cache_ttl = int(
        settings.get("account_validation.reset_password_cache_ttl_seconds", 7 * 24 * 60 * 60)
    )

    cache = registry.cache
    cache.set(cache_key, reset_password, ttl=cache_ttl)


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
    email_regexp = settings.get(
        "account_validation.email_regexp", "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
    )
    compiled_email_regexp = re.compile(email_regexp)
    if not compiled_email_regexp.match(user_email):
        error_details = {
            "name": "data.id",
            "description": f"The user id should match {email_regexp}.",
        }
        raise_invalid(request, **error_details)

    reset_password = str(uuid.uuid4())
    extra_data = {"reset-password": reset_password}
    hashed_reset_password = hash_password(reset_password)
    cache_reset_password(hashed_reset_password, user_id, request.registry)

    # Send a temporary reset password by mail.
    email_reset_password_subject_template = settings.get(
        "account_validation.email_reset_password_subject_template", "Reset password"
    )
    email_reset_password_body_template = settings.get(
        "account_validation.email_reset_password_body_template", "{reset-password}"
    )
    email_sender = settings.get("account_validation.email_sender", "admin@example.com")

    mailer = get_mailer(request)
    user_email_context = user.get(
        "email-context", {}
    )  # We might have some previous email context.
    try:
        data = request.json.get("data", {})
        email_context = data.get("email-context", user_email_context)
    except ValueError:
        email_context = user_email_context

    formatter = EmailFormatter()
    formatted_subject = formatter.format(
        email_reset_password_subject_template, **user, **extra_data, **email_context
    )
    formatted_body = formatter.format(
        email_reset_password_body_template, **user, **extra_data, **email_context
    )

    message = Message(
        subject=formatted_subject,
        sender=email_sender,
        recipients=[user_email],
        body=formatted_body,
    )
    mailer.send(message)

    return {"message": "A temporary reset password has been sent by mail"}
