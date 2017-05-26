"""
kinto.core.scripts: utilities to build admin scripts for kinto-based services
"""
import logging

import transaction as current_transaction
from pyramid.settings import asbool

from kinto.core.storage import exceptions as storage_exceptions
from kinto.plugins.quotas import scripts as quotas


logger = logging.getLogger(__name__)


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
                message = ('Cannot migrate the {} backend while '
                           'in readonly mode.'.format(backend))
                logger.error(message)
            else:
                getattr(registry, backend).initialize_schema(dry_run=dry_run)


def delete_collection(env, bucket_id, collection_id):
    registry = env['registry']
    settings = registry.settings
    readonly_mode = asbool(settings.get('readonly', False))

    if readonly_mode:
        message = ('Cannot delete the collection while in readonly mode.')
        logger.error(message)
        return 31

    bucket = '/buckets/{}'.format(bucket_id)
    collection = '/buckets/{}/collections/{}'.format(bucket_id, collection_id)

    try:
        registry.storage.get(collection_id='bucket',
                             parent_id='',
                             object_id=bucket_id)
    except storage_exceptions.RecordNotFoundError:
        logger.error("Bucket '{}' does not exist.".format(bucket))
        return 32

    try:
        registry.storage.get(collection_id='collection',
                             parent_id=bucket,
                             object_id=collection_id)
    except storage_exceptions.RecordNotFoundError:
        logger.error("Collection '{}' does not exist.".format(collection))
        return 33

    deleted = registry.storage.delete_all(collection_id='record',
                                          parent_id=collection,
                                          with_deleted=False)
    if len(deleted) == 0:
        logger.info("No records found for '{}'.".format(collection))
    else:
        logger.info('{} record(s) were deleted.'.format(len(deleted)))

    registry.storage.delete(collection_id='collection',
                            parent_id=bucket,
                            object_id=collection_id,
                            with_deleted=False)
    logger.info("'{}' collection object was deleted.".format(collection))

    record = ('/buckets/{bucket_id}'
              '/collections/{collection_id}'
              '/records/{record_id}')

    registry.permission.delete_object_permissions(
        collection,
        *[record.format(bucket_id=bucket_id,
                        collection_id=collection_id,
                        record_id=r['id']) for r in deleted])
    logger.info('Related permissions were deleted.')

    current_transaction.commit()

    return 0


def rebuild_quotas(env, dry_run=False):
    """Administrative command to rebuild quota usage information.

    This command recomputes the amount of space used by all
    collections and all buckets and updates the quota records in the
    storage backend to their correct values. This can be useful when
    cleaning up after a bug like e.g.
    https://github.com/Kinto/kinto/issues/1226.
    """
    registry = env['registry']
    settings = registry.settings
    readonly_mode = asbool(settings.get('readonly', False))

    # FIXME: readonly_mode is not meant to be a "maintenance mode" but
    # rather used with a database user that has read-only permissions.
    # If we ever introduce a maintenance mode, we should maybe enforce
    # it here.
    if readonly_mode:
        message = ('Cannot rebuild quotas while in readonly mode.')
        logger.error(message)
        return 31

    if 'kinto.plugins.quotas' not in settings['includes']:
        message = ('Cannot rebuild quotas when quotas plugin is not installed.')
        logger.error(message)
        return 32

    quotas.rebuild_quotas(registry.storage, dry_run=dry_run)
    current_transaction.commit()
    return 0
