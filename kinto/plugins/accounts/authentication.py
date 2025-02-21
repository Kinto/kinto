import bcrypt
from pyramid import authentication as base_auth

from kinto.core import utils
from kinto.core.storage import exceptions as storage_exceptions

from .utils import (
    ACCOUNT_CACHE_KEY,
    ACCOUNT_POLICY_NAME,
)


def account_check(username, password, request):
    settings = request.registry.settings
    hmac_secret = settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_CACHE_KEY.format(username))
    cache_ttl = int(settings.get("account_cache_ttl_seconds", 30))
    hashed_password = utils.hmac_digest(cache_key, password)

    # Check cache to see whether somebody has recently logged in with the same
    # username and password.
    cache = request.registry.cache
    cache_result = cache.get(cache_key)

    # Username and password have been verified previously. No need to compare hashes
    if cache_result == hashed_password:
        # Refresh the cache TTL.
        cache.expire(cache_key, cache_ttl)
        return True

    # Back to standard procedure
    parent_id = username
    try:
        existing = request.registry.storage.get(
            parent_id=parent_id, resource_name="account", object_id=username
        )
    except storage_exceptions.ObjectNotFoundError:
        return None

    hashed = existing["password"].encode(encoding="utf-8")
    pwd_str = password.encode(encoding="utf-8")
    # Check if password is valid (it is a very expensive computation)
    if bcrypt.checkpw(pwd_str, hashed):
        cache.set(cache_key, hashed_password, ttl=cache_ttl)
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
