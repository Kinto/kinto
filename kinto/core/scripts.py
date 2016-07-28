"""
kinto.core.scripts: utilities to build admin scripts for kinto-based services
"""

from __future__ import absolute_import, print_function
import warnings
import transaction as current_transaction
from pyramid.settings import asbool

from kinto.core.storage import exceptions as storage_exceptions


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
        message = ('Cannot delete the collection while in readonly mode.')
        warnings.warn(message)
        return 31

    bucket = '/buckets/%s' % bucket_id
    collection = '/buckets/%s/collections/%s' % (bucket_id, collection_id)

    try:
        registry.storage.get(collection_id='bucket',
                             parent_id='',
                             object_id=bucket_id)
    except storage_exceptions.RecordNotFoundError:
        print("Bucket %r does not exist." % bucket)
        return 33

    try:
        registry.storage.get(collection_id='collection',
                             parent_id=bucket,
                             object_id=collection_id)
    except storage_exceptions.RecordNotFoundError:
        print("Collection %r does not exist." % collection)
        return 33

    deleted = registry.storage.delete_all(collection_id='record',
                                          parent_id=collection,
                                          with_deleted=False)
    if deleted == 0:
        print('No records found for %r.' % collection)
    else:
        print('%d record(s) were deleted.' % len(deleted))

    registry.storage.delete(collection_id='collection',
                            parent_id=bucket,
                            object_id=collection_id,
                            with_deleted=False)
    print("%r collection object was deleted." % collection)

    record = ('/buckets/{bucket_id}'
              '/collections/{collection_id}'
              '/records/{record_id}')

    registry.permission.delete_object_permissions(
        collection,
        *[record.format(bucket_id=bucket_id,
                        collection_id=collection_id,
                        record_id=r['id']) for r in deleted])
    print('Related permissions were deleted.')

    current_transaction.commit()

    return 0
