import bcrypt
from pyramid import authentication as base_auth

from kinto.core import utils
from kinto.core.storage import exceptions as storage_exceptions

from .utils import (
    ACCOUNT_POLICY_NAME,
    cache_account,
    delete_cached_reset_password,
    get_account_cache_key,
    get_cached_account,
    get_cached_reset_password,
    is_validated,
    refresh_cached_account,
)


def account_check(username, password, request):
    settings = request.registry.settings
    validation_enabled = settings.get("account_validation", False)
    cache_key = get_account_cache_key(username, request.registry)
    hashed_password = utils.hmac_digest(cache_key, password)

    # Check cache to see whether somebody has recently logged in with the same
    # username and password.
    cache_result = get_cached_account(username, request.registry)

    # Username and password have been verified previously. No need to compare hashes
    if cache_result == hashed_password:
        # Refresh the cache TTL.
        refresh_cached_account(username, request.registry)
        return True

    # Back to standard procedure
    parent_id = username
    try:
        existing = request.registry.storage.get(
            parent_id=parent_id, resource_name="account", object_id=username
        )
    except storage_exceptions.ObjectNotFoundError:
        return None

    if validation_enabled and not is_validated(existing):
        return None

    hashed = existing["password"].encode(encoding="utf-8")
    pwd_str = password.encode(encoding="utf-8")
    # Check if password is valid (it is a very expensive computation)
    if bcrypt.checkpw(pwd_str, hashed):
        cache_account(hashed_password, username, request.registry)
        return True

    # Last chance, is this a "reset password" flow?
    return reset_password_flow(username, password, request)


def reset_password_flow(username, password, request):
    cache_key = get_account_cache_key(username, request.registry)
    hashed_password = utils.hmac_digest(cache_key, password)
    pwd_str = password.encode(encoding="utf-8")

    cached_password = get_cached_reset_password(username, request.registry)
    if not cached_password:
        return None

    # The temporary reset password is only available for changing a user's password.
    if request.method.lower() not in ["post", "put", "patch"]:
        return None

    # Only allow modifying a user account, no other resource.
    uri = utils.strip_uri_prefix(request.path)
    resource_name, _ = utils.view_lookup(request, uri)
    if resource_name != "account":
        return None

    try:
        data = request.json["data"]
    except (ValueError, KeyError):
        return None

    # Request one and only one data field: the `password`.
    if not data or "password" not in data or len(data.keys()) > 1:
        return None

    cached_password_str = cached_password.encode(encoding="utf-8")
    if bcrypt.checkpw(pwd_str, cached_password_str):
        # Remove the temporary reset password from the cache.
        delete_cached_reset_password(username, request.registry)
        cache_account(hashed_password, username, request.registry)
        return True


class AccountsAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    """Accounts authentication policy.

    It will check that the credentials exist in the account resource.
    """

    name = ACCOUNT_POLICY_NAME

    def __init__(self, *args, **kwargs):
        super().__init__(account_check, *args, **kwargs)

    def effective_principals(self, request):
        # Bypass default Pyramid construction of principals because
        # Pyramid multiauth already adds userid, Authenticated and Everyone
        # principals.
        return []
