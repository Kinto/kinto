def includeme(config):
    config.add_api_capability(
        'hawk',
        description='Hawk request authentication',
        url='https://kinto.readthedocs.io/en/latest/\
        configuration/settings.html#plugins')
