from kinto.core.events import ResourceChanged

from .listener import on_resource_changed


def includeme(config):
    config.add_api_capability('quotas',
                              description='Quotas Management on buckets '
                                          'and collections.',
                              url='https://kinto.readthedocs.io')

    # Listen to every resources (except history)
    config.add_subscriber(on_resource_changed, ResourceChanged,
                          for_resources=('bucket', 'group',
                                         'collection', 'record'))
