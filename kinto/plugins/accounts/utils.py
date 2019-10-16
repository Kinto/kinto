import bcrypt

from kinto.core import utils

ACCOUNT_CACHE_KEY = "accounts:{}:verified"
ACCOUNT_POLICY_NAME = "account"
ACCOUNT_RESET_PASSWORD_CACHE_KEY = "accounts:{}:reset-password"
ACCOUNT_VALIDATION_CACHE_KEY = "accounts:{}:validation-key"
DEFAULT_RESET_PASSWORD_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_VALIDATION_KEY_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


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


def get_account_cache_key(username, registry):
    """Given a username, return the cache key for this account."""
    settings = registry.settings
    hmac_secret = settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_CACHE_KEY.format(username))
    return cache_key


def cache_reset_password(reset_password, username, registry):
    """Store a reset-password in the cache."""
    settings = registry.settings
    hmac_secret = settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_RESET_PASSWORD_CACHE_KEY.format(username))
    # Store a reset password for 7 days by default.
    cache_ttl = int(
        settings.get(
            "account_validation.reset_password_cache_ttl_seconds",
            DEFAULT_RESET_PASSWORD_CACHE_TTL_SECONDS,
        )
    )

    cache = registry.cache
    cache_result = cache.set(cache_key, reset_password, ttl=cache_ttl)
    return cache_result


def get_cached_reset_password(username, registry):
    """Given a username, get the reset-password from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_RESET_PASSWORD_CACHE_KEY.format(username))

    cache = registry.cache
    cache_result = cache.get(cache_key)
    return cache_result


def delete_cached_reset_password(username, registry):
    """Given a username, delete the reset-password from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_RESET_PASSWORD_CACHE_KEY.format(username))

    cache = registry.cache
    cache_result = cache.delete(cache_key)
    return cache_result


def cache_validation_key(activation_key, username, registry):
    """Store a validation_key in the cache."""
    settings = registry.settings
    hmac_secret = settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_VALIDATION_CACHE_KEY.format(username))
    # Store an activation key for 7 days by default.
    cache_ttl = int(
        settings.get(
            "account_validation.validation_key_cache_ttl_seconds",
            DEFAULT_VALIDATION_KEY_CACHE_TTL_SECONDS,
        )
    )

    cache = registry.cache
    cache_result = cache.set(cache_key, activation_key, ttl=cache_ttl)
    return cache_result


def get_cached_validation_key(username, registry):
    """Given a username, get the validation key from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_VALIDATION_CACHE_KEY.format(username))
    cache = registry.cache
    activation_key = cache.get(cache_key)
    return activation_key


def delete_cached_validation_key(username, registry):
    """Given a username, delete the validation key from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_VALIDATION_CACHE_KEY.format(username))
    cache = registry.cache
    cache_result = cache.delete(cache_key)
    return cache_result


def cache_account(hashed_password, username, registry):
    """Store an authenticated account in the cache."""
    settings = registry.settings
    cache_ttl = int(settings.get("account_cache_ttl_seconds", 30))
    cache_key = get_account_cache_key(username, registry)
    cache = registry.cache
    cache_result = cache.set(cache_key, hashed_password, ttl=cache_ttl)
    return cache_result


def get_cached_account(username, registry):
    """Given a username, get the account from the cache."""
    cache_key = get_account_cache_key(username, registry)
    cache = registry.cache
    cached_account = cache.get(cache_key)
    return cached_account


def refresh_cached_account(username, registry):
    """Given a username, refresh the cache TTL."""
    settings = registry.settings
    cache_ttl = int(settings.get("account_cache_ttl_seconds", 30))
    cache_key = get_account_cache_key(username, registry)
    cache = registry.cache
    cache_result = cache.expire(cache_key, cache_ttl)
    return cache_result


def delete_cached_account(username, registry):
    """Given a username, delete the account key from the cache."""
    hmac_secret = registry.settings["userid_hmac_secret"]
    cache_key = utils.hmac_digest(hmac_secret, ACCOUNT_CACHE_KEY.format(username))
    cache = registry.cache
    cache_result = cache.delete(cache_key)
    return cache_result
