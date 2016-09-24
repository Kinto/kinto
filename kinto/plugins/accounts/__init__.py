from kinto.views import NameGenerator
from kinto.core.initialization import load_default_settings


DEFAULT_SETTINGS = {
    'account_create_principals': 'system.Everyone',
    'multiauth.policy.account.use': ('kinto.plugins.accounts.authentication.'
                                     'AccountsAuthenticationPolicy'),
}


def includeme(config):
    load_default_settings(config, DEFAULT_SETTINGS)

    # It's too late in the initialization sequence to set a default setting.
    config.registry.id_generators.setdefault('account', NameGenerator())

    config.add_api_capability(
        'accounts',
        description='Manage user accounts.',
        url='http://kinto.readthedocs.io/en/latest/api/1.x/accounts.html')

    config.scan('kinto.plugins.accounts.views')
