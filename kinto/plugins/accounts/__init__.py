from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from pyramid.exceptions import ConfigurationError

ACCOUNT_CACHE_KEY = 'accounts:{}:verified'
ACCOUNT_POLICY_NAME = 'account'


def includeme(config):
    config.add_api_capability(
        'accounts',
        description='Manage user accounts.',
        url='https://kinto.readthedocs.io/en/latest/api/1.x/accounts.html')

    config.scan('kinto.plugins.accounts.views')

    PERMISSIONS_INHERITANCE_TREE['root'].update({
        'account:create': {}
    })
    PERMISSIONS_INHERITANCE_TREE['account'] = {
        'write': {'account': ['write']},
        'read': {'account': ['write', 'read']}
    }

    # Add some safety to avoid weird behaviour with basicauth default policy.
    settings = config.get_settings()
    auth_policies = settings['multiauth.policies']
    if 'basicauth' in auth_policies and 'account' in auth_policies:
        if auth_policies.index('basicauth') < auth_policies.index('account'):
            error_msg = ("'basicauth' should not be mentioned before 'account' "
                         "in 'multiauth.policies' setting.")
            raise ConfigurationError(error_msg)

    # We assume anyone in account_create_principals is to create
    # accounts for other people.
    # No one can create accounts for other people unless they are an
    # "admin", defined as someone matching account_write_principals.
    # Therefore any account that is in account_create_principals
    # should be in account_write_principals too.
    creators = set(settings.get('account_create_principals', '').split())
    admins = set(settings.get('account_write_principals', '').split())
    cant_create_anything = creators.difference(admins)
    # system.Everyone isn't an account.
    cant_create_anything.discard('system.Everyone')
    if cant_create_anything:
        message = ('Configuration has some principals in account_create_principals '
                   'but not in account_write_principals. These principals will only be '
                   'able to create their own accounts. This may not be what you want.\n'
                   'If you want these users to be able to create accounts for other users, '
                   'add them to account_write_principals.\n'
                   'Affected users: {}'.format(list(cant_create_anything)))

        raise ConfigurationError(message)
