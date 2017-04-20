from kinto.core.events import ResourceChanged

from .listener import on_resource_changed


def includeme(config):
    config.add_api_capability(
        'history',
        description='Track changes on data.',
        url='http://kinto.readthedocs.io/en/latest/api/1.x/history.html')

    # Activate end-points.
    config.scan('kinto.plugins.history.views')

    # Listen to every resources (except history)
    config.add_subscriber(on_resource_changed, ResourceChanged,
                          for_resources=('bucket', 'group',
                                         'collection', 'record'))
