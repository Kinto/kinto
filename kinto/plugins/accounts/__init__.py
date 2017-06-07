from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from pyramid.exceptions import ConfigurationError


def includeme(config):
    config.add_api_capability(
        'accounts',
        description='Manage user accounts.',
        url='https://kinto.readthedocs.io/en/latest/api/1.x/accounts.html')

    config.scan('kinto.plugins.accounts.views')

    PERMISSIONS_INHERITANCE_TREE[''].update({
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
