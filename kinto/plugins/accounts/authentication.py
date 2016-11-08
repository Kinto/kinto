from pyramid import authentication as base_auth

from kinto.core.storage import exceptions as storage_exceptions


def account_check(username, password, request):
    # parent_id = request.prefixed_userid
    # if parent_id is None:
    #     parent_id = request.json['data']['id']
    parent_id = username
    print username

    # if 'system.Authenticated' not in request.effective_principals:
    #     parent_id = request.unauthenticated_userid
    # parent_id = request.json['data']['id']

    try:
        existing = request.registry.storage.get(parent_id=parent_id,
                                                collection_id='account',
                                                object_id=username)
    except storage_exceptions.RecordNotFoundError:
        return None
    # XXX: bcrypt whatever
    if existing['password'] == password:
        return True  # anything but None.


class AccountsAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    """Accounts authentication policy.

    It will check that the credentials exist in the account resource.
    """
    def __init__(self, *args, **kwargs):
        super(AccountsAuthenticationPolicy, self).__init__(account_check, *args, **kwargs)

    def effective_principals(self, request):
        # Bypass default Pyramid construction of principals because
        # Pyramid multiauth already adds userid, Authenticated and Everyone
        # principals.
        return []
