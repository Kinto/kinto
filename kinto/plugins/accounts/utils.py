import bcrypt
import string

from kinto.core import utils


ACCOUNT_CACHE_KEY = "accounts:{}:verified"
ACCOUNT_POLICY_NAME = "account"
ACCOUNT_RESET_PASSWORD_CACHE_KEY = "accounts:{}:reset-password"
ACCOUNT_VALIDATION_CACHE_KEY = "accounts:{}:validation-key"


def hash_password(password):
    # Store password safely in database as str
    # (bcrypt.hashpw returns base64 bytes).
    pwd_str = password.encode(encoding="utf-8")
    hashed = bcrypt.hashpw(pwd_str, bcrypt.gensalt())
    return hashed.decode(encoding="utf-8")


def is_validated(user):
    """Is this user record validated?"""
    # An account is "validated" if it has the `validated` field set to True, or
    # no `validated` field at all (for accounts created before the "account
    # validation option" was enabled).
    return user.get("validated", True)


def get_cached_reset_password(username, registry):
    """Given a username, get the reset-password from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_RESET_PASSWORD_CACHE_KEY.format(username))

    cache = registry.cache
    cache_result = cache.get(cache_key)
    return cache_result


class EmailFormatter(string.Formatter):
    """Formatter class that will not fail if there's a missing key."""

    def __init__(self, default="{{{0}}}"):
        self.default = default

    def get_value(self, key, args, kwargs):
        return kwargs.get(key, self.default.format(key))
