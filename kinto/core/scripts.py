"""
kinto.core.scripts: utilities to build admin scripts for kinto-based services
"""

from __future__ import absolute_import, print_function
import warnings

from pyramid.settings import asbool


def migrate(env, dry_run=False):
    """
    User-friendly frontend to run database migrations.
    """
    registry = env['registry']
    settings = registry.settings
    readonly_backends = ('storage', 'permission')
    readonly_mode = asbool(settings.get('readonly', False))

    for backend in ('cache', 'storage', 'permission'):
        if hasattr(registry, backend):
            if readonly_mode and backend in readonly_backends:
                message = ('Cannot migrate the %s backend while '
                           'in readonly mode.' % backend)
                warnings.warn(message)
            else:
                getattr(registry, backend).initialize_schema(dry_run=dry_run)


def delete_collection(env, bucket_id, collection_id):
    registry = env['registry']
    settings = registry.settings
    readonly_mode = asbool(settings.get('readonly', False))

    if readonly_mode:
        message = ('Cannot cleanup the collection while in readonly mode.')
        warnings.warn(message)
        return 31

    collection = '/buckets/%s/collections/%s' % (bucket_id, collection_id)
    deleted = registry.storage.delete_all('record', collection,
                                          with_deleted=False)
    print('%d records have been deleted.' % len(deleted))

    bucket = '/buckets/%s' % bucket_id
    registry.storage.delete('collection', bucket, collection_id,
                            with_deleted=False)
    print('%r collection has been deleted.' % collection)

    record = ('/buckets/{bucket_id}'
              '/collections/{collection_id}'
              '/records/{record_id}')

    registry.permission.delete_object_permissions(
        collection.rstrip('/'),
        *[record.format(bucket_id=bucket_id,
                        collection_id=collection_id,
                        record_id=r['id']) for r in deleted])
    print('Related permissions cleaned up.')

    return 0
