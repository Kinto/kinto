import re

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from pyramid.exceptions import ConfigurationError

from .authentication import AccountsAuthenticationPolicy as AccountsPolicy
from .utils import (
    ACCOUNT_CACHE_KEY,
    ACCOUNT_POLICY_NAME,
    ACCOUNT_RESET_PASSWORD_CACHE_KEY,
    ACCOUNT_VALIDATION_CACHE_KEY,
)


__all__ = [
    "ACCOUNT_CACHE_KEY",
    "ACCOUNT_POLICY_NAME",
    "ACCOUNT_RESET_PASSWORD_CACHE_KEY",
    "ACCOUNT_VALIDATION_CACHE_KEY",
    "AccountsPolicy",
]

DOCS_URL = "https://kinto.readthedocs.io/en/stable/api/1.x/accounts.html"


def includeme(config):
    settings = config.get_settings()
    validation_enabled = settings.get("account_validation", False)
    config.add_api_capability(
        "accounts",
        description="Manage user accounts.",
        url="https://kinto.readthedocs.io/en/latest/api/1.x/accounts.html",
        validation_enabled=validation_enabled,
    )
    kwargs = {}
    if not validation_enabled:
        kwargs["ignore"] = "kinto.plugins.accounts.views.validation"
    config.scan("kinto.plugins.accounts.views", **kwargs)

    PERMISSIONS_INHERITANCE_TREE["root"].update({"account:create": {}})
    PERMISSIONS_INHERITANCE_TREE["account"] = {
        "write": {"account": ["write"]},
        "read": {"account": ["write", "read"]},
    }

    if validation_enabled:
        # Valid mailers other than the default are `debug` and `testing`
        # according to
        # https://docs.pylonsproject.org/projects/pyramid_mailer/en/latest/#debugging
        mailer = settings.get("mail.mailer", "")
        config.include("pyramid_mailer" + (f".{mailer}" if mailer else ""))

    # Check that the account policy is mentioned in config if included.
    accountClass = "AccountsPolicy"
    policy = None
    for k, v in settings.items():
        m = re.match("multiauth\\.policy\\.(.*)\\.use", k)
        if m:
            if v.endswith(accountClass) or v.endswith("AccountsAuthenticationPolicy"):
                policy = m.group(1)

    if not policy:
        error_msg = (
            "Account policy missing the 'multiauth.policy.*.use' "
            f"setting. See {accountClass} in docs {DOCS_URL}."
        )
        raise ConfigurationError(error_msg)

    # Add some safety to avoid weird behaviour with basicauth default policy.
    auth_policies = settings["multiauth.policies"]
    if "basicauth" in auth_policies and policy in auth_policies:
        if auth_policies.index("basicauth") < auth_policies.index(policy):
            error_msg = (
                "'basicauth' should not be mentioned before '%s' "
                "in 'multiauth.policies' setting."
            ) % policy
            raise ConfigurationError(error_msg)

    # We assume anyone in account_create_principals is to create
    # accounts for other people.
    # No one can create accounts for other people unless they are an
    # "admin", defined as someone matching account_write_principals.
    # Therefore any account that is in account_create_principals
    # should be in account_write_principals too.
    creators = set(settings.get("account_create_principals", "").split())
    admins = set(settings.get("account_write_principals", "").split())
    cant_create_anything = creators.difference(admins)
    # system.Everyone isn't an account.
    cant_create_anything.discard("system.Everyone")
    if cant_create_anything:
        message = (
            "Configuration has some principals in account_create_principals "
            "but not in account_write_principals. These principals will only be "
            "able to create their own accounts. This may not be what you want.\n"
            "If you want these users to be able to create accounts for other users, "
            "add them to account_write_principals.\n"
            f"Affected users: {list(cant_create_anything)}"
        )

        raise ConfigurationError(message)
