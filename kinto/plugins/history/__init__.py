import copy
from datetime import datetime

from kinto.core.events import ResourceChanged


def on_resource_changed(event):
    """
    Everytime an object is created/changed/deleted, we create an entry in the
    ``history`` resource. The entries are served as read-only in the
    :mod:`kinto.plugins.history.views` module.
    """
    userid = event.request.prefixed_userid
    payload = copy.deepcopy(event.payload)
    action = payload['action']
    bucket_id = payload.pop('bucket_id')
    bucket_uri = '/buckets/%s' % bucket_id
    resource_name = payload['resource_name']
    event_uri = payload['uri']

    storage = event.request.registry.storage
    permission = event.request.registry.permission

    # XXX instead of this, modify on_buckets_delete() to remove from
    # storage every object whose parent_id starts with /buckets/{id}
    if resource_name == 'bucket' and action == 'delete':
        storage.delete_all(parent_id=bucket_uri,
                           collection_id='history')
        return

    for impacted in event.impacted_records:
        target = impacted['new' if action != 'delete' else 'old']
        # On POST .../records, the URI does not contain the newly created
        # record id. Make sure it does:
        obj_id = target['id']
        payload.setdefault('%s_id' % resource_name, obj_id)
        if not event_uri.endswith(obj_id):
            payload['uri'] = event_uri + '/' + obj_id

        # Prepare the history entry attributes.
        # XXX: Fetching the permissions of each impacted records one by one
        # is not efficient.
        perms = permission.get_object_permissions(payload['uri'])
        attrs = dict(userid=userid,
                     date=datetime.now().isoformat(),
                     target={'data': target, 'permissions': perms},
                     **payload)

        # Create a record for the 'history' resource, whose parent_id is
        # the bucket URI (c.f. views.py).
        # Note: this will be rolledback if the transaction is rolledback.
        entry = storage.create(parent_id=bucket_uri,
                               collection_id='history',
                               record=attrs)

        # XXX : careful, for each impacted record
        read_principals = set(perms.get('read', []))
        read_principals.update(perms.get('write', []))

        bucket_uri = '/buckets/%s' % bucket_id
        bucket_perms = permission.get_object_permissions(bucket_uri)
        read_principals.update(bucket_perms.get('read', []))
        read_principals.update(bucket_perms.get('write', []))

        if 'collection_id' in payload:
            collection_uri = bucket_uri + '/collections/%s' % payload['collection_id']
            collection_perms = permission.get_object_permissions(collection_uri)
            read_principals.update(collection_perms.get('read', []))
            read_principals.update(collection_perms.get('write', []))

        entry_perm_id = '/buckets/%s/history/%s' % (bucket_id, entry['id'])
        for principal in read_principals:
            permission.add_principal_to_ace(entry_perm_id, 'read', principal)


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
