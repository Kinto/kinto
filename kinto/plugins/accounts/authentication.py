import bcrypt
from pyramid import authentication as base_auth

from kinto.core.storage import exceptions as storage_exceptions


def account_check(username, password, request):
    parent_id = username
    try:
        existing = request.registry.storage.get(parent_id=parent_id,
                                                collection_id='account',
                                                object_id=username)
    except storage_exceptions.RecordNotFoundError:
        return None

    hashed = existing['password'].encode(encoding='utf-8')
    pwd_str = password.encode(encoding='utf-8')
    if hashed == bcrypt.hashpw(pwd_str, hashed):
        return True  # Match! Return anything but None.


class AccountsAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    """Accounts authentication policy.

    It will check that the credentials exist in the account resource.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(account_check, *args, **kwargs)

    def effective_principals(self, request):
        # Bypass default Pyramid construction of principals because
        # Pyramid multiauth already adds userid, Authenticated and Everyone
        # principals.
        return []
