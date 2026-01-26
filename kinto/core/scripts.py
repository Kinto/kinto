"""
kinto.core.scripts: utilities to build admin scripts for kinto-based services
"""

import logging

from pyramid.settings import asbool

from kinto.core.storage import (
    DEFAULT_DELETED_FIELD,
    DEFAULT_ID_FIELD,
    DEFAULT_MODIFIED_FIELD,
)
from kinto.core.storage.exceptions import ObjectNotFoundError
from kinto.core.utils import _parse_collection_path


logger = logging.getLogger(__name__)


def migrate(env, dry_run=False):
    """
    User-friendly frontend to run database migrations.
    """
    registry = env["registry"]
    settings = registry.settings
    readonly_backends = ("storage", "permission")
    readonly_mode = asbool(settings.get("readonly", False))

    for backend in ("cache", "storage", "permission"):
        if hasattr(registry, backend):
            if readonly_mode and backend in readonly_backends:
                message = f"Cannot migrate the {backend} backend while in readonly mode."
                logger.error(message)
            else:
                getattr(registry, backend).initialize_schema(dry_run=dry_run)


def purge_deleted(env, resource_names, max_retained):
    logger.info("Keep only %r tombstones per parent and resource." % max_retained)

    registry = env["registry"]

    count = 0
    for resource_name in resource_names:
        count += registry.storage.purge_deleted(
            resource_name=resource_name, parent_id="*", max_retained=max_retained
        )

    logger.info("%s tombstone(s) deleted." % count)
    return 0


def rename_collection(env, src, dst, dry_run=False, force=False):
    """Rename a collection from ``src`` to ``dst``.

    This moves the collection object, its records (including tombstones), and
    the corresponding permissions.
    """
    registry = env["registry"]
    storage = registry.storage
    permission = getattr(registry, "permission", None)

    # Parse paths
    src_bucket, src_collection = _parse_collection_path(src)
    dst_bucket, dst_collection = _parse_collection_path(dst)

    if src == dst:
        logger.error("Source and destination are identical: %s", src)
        raise ValueError("Source and destination must be different")

    src_bucket_uri = f"/buckets/{src_bucket}"
    dst_bucket_uri = f"/buckets/{dst_bucket}"
    src_collection_uri = f"{src_bucket_uri}/collections/{src_collection}"
    dst_collection_uri = f"{dst_bucket_uri}/collections/{dst_collection}"

    # Ensure source collection exists
    try:
        src_collection_obj = storage.get("collection", src_bucket_uri, src_collection)
    except ObjectNotFoundError:
        logger.error("Source collection does not exist: %s", src)
        raise

    # Ensure destination bucket exists
    try:
        storage.get("bucket", "", dst_bucket)
    except ObjectNotFoundError:
        logger.error("Destination bucket does not exist: %s", dst_bucket)
        raise

    # Check destination collection
    dest_exists = True
    try:
        storage.get("collection", dst_bucket_uri, dst_collection)
    except ObjectNotFoundError:
        dest_exists = False

    if dest_exists and not force:
        logger.error("Destination collection already exists: %s", dst)
        raise ValueError("Destination exists (use --force to overwrite)")

    # Dry-run: just print what would be done
    if dry_run:
        records = storage.list_all("record", src_collection_uri, include_deleted=True)
        record_count = len(records)
        tombstone_count = sum(1 for r in records if r.get(DEFAULT_DELETED_FIELD))
        logger.info("[dry-run] would rename %s -> %s (%d records, %d tombstones)", src, dst, record_count, tombstone_count)
        return 0

    # If force and destination exists, delete it first.
    if dest_exists and force:
        # Delete all records in destination collection
        records = storage.list_all("record", dst_collection_uri, include_deleted=True)
        for r in records:
            try:
                storage.delete("record", dst_collection_uri, r[DEFAULT_ID_FIELD])
            except Exception as e:
                # Log errors during cleanup; record might already be deleted or have permission issues
                logger.warning("Failed to delete destination record %s: %s", r[DEFAULT_ID_FIELD], e)
        # Delete collection itself
        try:
            storage.delete("collection", dst_bucket_uri, dst_collection)
        except Exception as e:
            # Log errors during cleanup; collection might already be deleted
            logger.warning("Failed to delete destination collection %s: %s", dst_collection, e)
        # Remove destination permissions
        if permission:
            permission.delete_object_permissions(dst_collection_uri, f"{dst_collection_uri}/*")

    # Create collection at destination (preserve metadata and timestamps)
    new_collection_obj = {k: v for k, v in src_collection_obj.items()}
    new_collection_obj["id"] = dst_collection
    storage.create("collection", dst_bucket_uri, new_collection_obj)

    # Copy permissions for collection
    if permission:
        perms = permission.get_objects_permissions([src_collection_uri])
        if perms:
            collection_perms = perms[0]
            permission.replace_object_permissions(dst_collection_uri, collection_perms)

    # Copy records
    records = storage.list_all("record", src_collection_uri, include_deleted=True)
    record_count = len(records)
    tombstone_count = sum(1 for r in records if r.get(DEFAULT_DELETED_FIELD))
    logger.info("Moving %d records (%d tombstones) from %s to %s", record_count, tombstone_count, src, dst)
    for r in records:
        obj_id = r[DEFAULT_ID_FIELD]
        src_obj_uri = f"{src_collection_uri}/records/{obj_id}"
        dst_parent = dst_collection_uri
        dst_obj_uri = f"{dst_parent}/records/{obj_id}"

        if r.get(DEFAULT_DELETED_FIELD):
            # Recreate tombstone at destination
            # Create a minimal representation and delete it to produce tombstone.
            storage.create(
                "record",
                dst_parent,
                {"id": obj_id, DEFAULT_MODIFIED_FIELD: r[DEFAULT_MODIFIED_FIELD]},
            )
            storage.delete("record", dst_parent, obj_id, last_modified=r[DEFAULT_MODIFIED_FIELD])
        else:
            new_obj = {k: v for k, v in r.items()}
            new_obj["id"] = obj_id
            storage.create("record", dst_parent, new_obj)

        # Copy permissions for the record
        if permission:
            perms = permission.get_objects_permissions([src_obj_uri])
            if perms:
                record_perms = perms[0]
                permission.replace_object_permissions(dst_obj_uri, record_perms)

    # Remove source permissions
    if permission:
        permission.delete_object_permissions(src_collection_uri, f"{src_collection_uri}/*")

    # Delete records and collection at source
    for r in records:
        obj_id = r[DEFAULT_ID_FIELD]
        try:
            storage.delete("record", src_collection_uri, obj_id)
        except Exception as e:
            # Log errors during cleanup; record might already be deleted
            logger.warning("Failed to delete source record %s: %s", obj_id, e)
    try:
        storage.delete("collection", src_bucket_uri, src_collection)
    except Exception as e:
        # Log errors during cleanup; collection might already be deleted
        logger.warning("Failed to delete source collection %s: %s", src_collection, e)

    logger.info("Renamed %s -> %s (%d records, %d tombstones)", src, dst, record_count, tombstone_count)
    return 0


def flush_cache(env):
    registry = env["registry"]
    registry.cache.flush()
    logger.info("Cache has been cleared.")
    return 0
