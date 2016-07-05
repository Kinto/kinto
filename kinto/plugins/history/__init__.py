from datetime import datetime

from kinto.core.events import ResourceChanged


def on_resource_changed(event):
    action = event.payload['action']
    uri = event.payload['uri']
    bucket_id = event.payload['bucket_id']
    bucket_uri = '/buckets/%s' % bucket_id

    # XXX: POST on /buckets/test/collections does not give collection_id

    userid = event.request.prefixed_userid

    storage = event.request.registry.storage
    permission = event.request.registry.permission

    for impacted in event.impacted_records:
        perms = permission.get_object_permissions(uri)

        target = impacted['new' if action != 'delete' else 'old']
        attrs = dict(userid=userid,
                     date=datetime.now().isoformat(),
                     target={'data': target, 'permissions': perms},
                     **event.payload)
        storage.create(parent_id=bucket_uri,
                       collection_id='history',
                       record=attrs)


def includeme(config):
    config.add_api_capability('history',
                              description='Track changes on data.',
                              url='https://kinto.readthedocs.io')

    # Activate end-points.
    config.scan('kinto.plugins.history.views')

    # Listen to every resources (except history)
    config.add_subscriber(on_resource_changed, ResourceChanged,
                          for_resources=('bucket', 'group',
                                         'collection', 'record'))
