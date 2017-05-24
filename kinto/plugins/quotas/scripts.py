"""
kinto.plugins.quotas.scripts: scripts to maintain quotas and fix them when they're broken
"""
import logging

from kinto.core.storage import Sort
from kinto.core.storage.utils import paginated
from .listener import BUCKET_QUOTA_OBJECT_ID, COLLECTION_QUOTA_OBJECT_ID
from .utils import record_size

logger = logging.getLogger(__name__)

OLDEST_FIRST = Sort("last_modified", 1)


def rebuild_quotas(storage, dry_run=False):
    for bucket in paginated(storage, collection_id='bucket',
                            parent_id='', sorting=[OLDEST_FIRST]):
        bucket_id = bucket['id']
        bucket_path = '/buckets/{}'.format(bucket['id'])
        bucket_record_count = 0
        bucket_storage_size = record_size(bucket)

        for collection in paginated(storage, collection_id='collection',
                                    parent_id=bucket_path, sorting=[OLDEST_FIRST]):
            collection_info = rebuild_quotas_collection(storage, bucket_id, collection, dry_run)
            (collection_record_count, collection_storage_size) = collection_info
            bucket_record_count += collection_record_count
            bucket_storage_size += collection_storage_size

        bucket_record = {"record_count": bucket_record_count, "storage_size": bucket_storage_size}
        if not dry_run:
            storage.update(collection_id='quota', parent_id=bucket_path,
                           object_id=BUCKET_QUOTA_OBJECT_ID, record=bucket_record)

        logger.info("Bucket {}. Final size: {} records, {} bytes.".format(
            bucket_id, bucket_record_count, bucket_storage_size))


def rebuild_quotas_collection(storage, bucket_id, collection, dry_run=False):
    """Helper method for rebuild_quotas that updates a single collection."""
    collection_id = collection['id']
    collection_record_count = 0
    collection_storage_size = record_size(collection)
    collection_path = '/buckets/{}/collections/{}'.format(bucket_id, collection_id)
    for record in paginated(storage, collection_id='record',
                            parent_id=collection_path, sorting=[OLDEST_FIRST]):
        collection_record_count += 1
        collection_storage_size += record_size(record)

    logger.info("Bucket {}, collection {}. Final size: {} records, {} bytes.".format(
        bucket_id, collection_id, collection_record_count, collection_storage_size))
    new_quota_info = {
        "record_count": collection_record_count,
        "storage_size": collection_storage_size,
    }
    if not dry_run:
        storage.update(collection_id='quota', parent_id=collection_path,
                       object_id=COLLECTION_QUOTA_OBJECT_ID, record=new_quota_info)
    return (collection_record_count, collection_storage_size)
