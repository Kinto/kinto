from kinto.views import NameGenerator
from kinto.authorization import PERMISSIONS_INHERITANCE_TREE


def includeme(config):
    config.add_api_capability(
        'accounts',
        description='Manage user accounts.',
        url='https://kinto.readthedocs.io/en/latest/api/1.x/accounts.html')

    # It's too late in the initialization sequence to set a default setting.
    config.registry.id_generators.setdefault('account', NameGenerator())
    config.scan('kinto.plugins.accounts.views')

    PERMISSIONS_INHERITANCE_TREE[''].update({
        'account:create': {}
    })
    PERMISSIONS_INHERITANCE_TREE['account'] = {
        'write': {'account': ['write']},
        'read': {'account': ['write', 'read']}
    }
