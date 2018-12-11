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
    for bucket in paginated(storage, resource_name="bucket", parent_id="", sorting=[OLDEST_FIRST]):
        bucket_id = bucket["id"]
        bucket_path = f"/buckets/{bucket['id']}"
        bucket_collection_count = 0
        bucket_record_count = 0
        bucket_storage_size = record_size(bucket)

        for collection in paginated(
            storage, resource_name="collection", parent_id=bucket_path, sorting=[OLDEST_FIRST]
        ):
            collection_info = rebuild_quotas_collection(storage, bucket_id, collection, dry_run)
            (collection_record_count, collection_storage_size) = collection_info
            bucket_collection_count += 1
            bucket_record_count += collection_record_count
            bucket_storage_size += collection_storage_size

        bucket_record = {
            "record_count": bucket_record_count,
            "storage_size": bucket_storage_size,
            "collection_count": bucket_collection_count,
        }
        if not dry_run:
            storage.update(
                resource_name="quota",
                parent_id=bucket_path,
                object_id=BUCKET_QUOTA_OBJECT_ID,
                obj=bucket_record,
            )

        logger.info(
            f"Bucket {bucket_id}. Final size: {bucket_collection_count} collections, {bucket_record_count} records, {bucket_storage_size} bytes."
        )


def rebuild_quotas_collection(storage, bucket_id, collection, dry_run=False):
    """Helper method for rebuild_quotas that updates a single collection."""
    collection_id = collection["id"]
    collection_record_count = 0
    collection_storage_size = record_size(collection)
    collection_uri = f"/buckets/{bucket_id}/collections/{collection_id}"
    for record in paginated(
        storage, resource_name="record", parent_id=collection_uri, sorting=[OLDEST_FIRST]
    ):
        collection_record_count += 1
        collection_storage_size += record_size(record)

    logger.info(
        f"Bucket {bucket_id}, collection {collection_id}. Final size: {collection_record_count} records, {collection_storage_size} bytes."
    )
    new_quota_info = {
        "record_count": collection_record_count,
        "storage_size": collection_storage_size,
    }
    if not dry_run:
        storage.update(
            resource_name="quota",
            parent_id=collection_uri,
            object_id=COLLECTION_QUOTA_OBJECT_ID,
            obj=new_quota_info,
        )
    return (collection_record_count, collection_storage_size)
