import copy

from pyramid.httpexceptions import HTTPInsufficientStorage

from kinto.core.errors import ERRORS, http_error
from kinto.core.storage.exceptions import ObjectNotFoundError
from kinto.core.utils import instance_uri

from .utils import record_size

QUOTA_RESOURCE_NAME = "quota"
BUCKET_QUOTA_OBJECT_ID = "bucket_info"
COLLECTION_QUOTA_OBJECT_ID = "collection_info"


def raise_insufficient_storage(message):
    raise http_error(HTTPInsufficientStorage(), errno=ERRORS.FORBIDDEN.value, message=message)


def get_bucket_settings(settings, bucket_id, name):
    return settings.get(
        # Bucket specific
        f"quotas.bucket_{bucket_id}_{name}",
        # Global to all buckets
        settings.get(f"quotas.bucket_{name}", None),
    )


def get_collection_settings(settings, bucket_id, collection_id, name):
    return settings.get(
        # Specific for a given bucket collection
        f"quotas.collection_{bucket_id}_{collection_id}_{name}",
        # Specific to given bucket collections
        settings.get(
            f"quotas.collection_{bucket_id}_{name}",
            # Global to all buckets collections
            settings.get(f"quotas.collection_{name}", None),
        ),
    )


def on_resource_changed(event):
    """
    Everytime an object is created/changed/deleted, we update the
    bucket counters.

    If a new object exceeds the quotas, we reject the request.
    """
    payload = event.payload
    action = payload["action"]
    resource_name = payload["resource_name"]

    if action == "delete" and resource_name == "bucket":
        # Deleting a bucket already deletes everything underneath (including
        # quotas info). See kinto/views/bucket.
        return

    settings = event.request.registry.settings

    event_uri = payload["uri"]
    bucket_id = payload["bucket_id"]
    bucket_uri = instance_uri(event.request, "bucket", id=bucket_id)
    collection_id = None
    collection_uri = None
    if "collection_id" in payload:
        collection_id = payload["collection_id"]
        collection_uri = instance_uri(
            event.request, "collection", bucket_id=bucket_id, id=collection_id
        )

    bucket_max_bytes = get_bucket_settings(settings, bucket_id, "max_bytes")
    bucket_max_items = get_bucket_settings(settings, bucket_id, "max_items")
    bucket_max_bytes_per_item = get_bucket_settings(settings, bucket_id, "max_bytes_per_item")
    collection_max_bytes = get_collection_settings(settings, bucket_id, collection_id, "max_bytes")
    collection_max_items = get_collection_settings(settings, bucket_id, collection_id, "max_items")
    collection_max_bytes_per_item = get_collection_settings(
        settings, bucket_id, collection_id, "max_bytes_per_item"
    )

    max_bytes_per_item = collection_max_bytes_per_item or bucket_max_bytes_per_item

    storage = event.request.registry.storage

    targets = []
    for impacted in event.impacted_objects:
        target = impacted["new" if action != "delete" else "old"]
        # On POST .../records, the URI does not contain the newly created
        # record id.
        obj_id = target["id"]
        parts = event_uri.split("/")
        if resource_name in parts[-1]:
            parts.append(obj_id)
        else:
            # Make sure the id is correct on grouped events.
            parts[-1] = obj_id
        uri = "/".join(parts)

        old = impacted.get("old", {})
        new = impacted.get("new", {})

        targets.append((uri, obj_id, old, new))

    try:
        bucket_info = copy.deepcopy(
            storage.get(
                parent_id=bucket_uri,
                resource_name=QUOTA_RESOURCE_NAME,
                object_id=BUCKET_QUOTA_OBJECT_ID,
            )
        )
    except ObjectNotFoundError:
        bucket_info = {"collection_count": 0, "record_count": 0, "storage_size": 0}

    collection_info = {"record_count": 0, "storage_size": 0}
    if collection_id:
        try:
            collection_info = copy.deepcopy(
                storage.get(
                    parent_id=collection_uri,
                    resource_name=QUOTA_RESOURCE_NAME,
                    object_id=COLLECTION_QUOTA_OBJECT_ID,
                )
            )
        except ObjectNotFoundError:
            pass

    # Update the bucket quotas values for each impacted record.
    for (uri, obj_id, old, new) in targets:
        old_size = record_size(old)
        new_size = record_size(new)

        if max_bytes_per_item is not None and action != "delete":
            if new_size > max_bytes_per_item:
                message = f'Maximum bytes per object exceeded " "({new_size} > {max_bytes_per_item} Bytes.'
                raise_insufficient_storage(message)

        if action == "create":
            bucket_info["storage_size"] += new_size
            if resource_name == "collection":
                bucket_info["collection_count"] += 1
                collection_info["storage_size"] += new_size
            if resource_name == "record":
                bucket_info["record_count"] += 1
                collection_info["record_count"] += 1
                collection_info["storage_size"] += new_size
        elif action == "update":
            bucket_info["storage_size"] -= old_size
            bucket_info["storage_size"] += new_size
            if resource_name in ("collection", "record"):
                collection_info["storage_size"] -= old_size
                collection_info["storage_size"] += new_size
        else:  # action == 'delete':
            bucket_info["storage_size"] -= old_size
            if resource_name == "collection":
                collection_uri = uri
                bucket_info["collection_count"] -= 1
                # When we delete the collection all the records in it
                # are deleted without notification.
                collection_records = storage.list_all(
                    resource_name="record", parent_id=collection_uri
                )
                for r in collection_records:
                    old_record_size = record_size(r)
                    bucket_info["record_count"] -= 1
                    bucket_info["storage_size"] -= old_record_size
                    collection_info["record_count"] -= 1
                    collection_info["storage_size"] -= old_record_size
                collection_info["storage_size"] -= old_size

            if resource_name == "record":
                bucket_info["record_count"] -= 1
                collection_info["record_count"] -= 1
                collection_info["storage_size"] -= old_size

    if bucket_max_bytes is not None:
        if bucket_info["storage_size"] > bucket_max_bytes:
            message = (
                "Bucket maximum total size exceeded "
                f"({bucket_info['storage_size']} > {bucket_max_bytes} Bytes). "
            )
            raise_insufficient_storage(message)

    if bucket_max_items is not None:
        if bucket_info["record_count"] > bucket_max_items:
            message = (
                "Bucket maximum number of objects exceeded "
                f"({bucket_info['record_count']} > {bucket_max_items} objects)."
            )
            raise_insufficient_storage(message)

    if collection_max_bytes is not None:
        if collection_info["storage_size"] > collection_max_bytes:
            message = (
                "Collection maximum size exceeded "
                f"({collection_info['storage_size']} > {collection_max_bytes} Bytes)."
            )
            raise_insufficient_storage(message)

    if collection_max_items is not None:
        if collection_info["record_count"] > collection_max_items:
            message = (
                "Collection maximum number of objects exceeded "
                f"({collection_info['record_count']} > {collection_max_items} objects)."
            )
            raise_insufficient_storage(message)

    storage.update(
        parent_id=bucket_uri,
        resource_name=QUOTA_RESOURCE_NAME,
        object_id=BUCKET_QUOTA_OBJECT_ID,
        obj=bucket_info,
    )

    if collection_id:
        if action == "delete" and resource_name == "collection":
            # Deleting a collection already deletes everything underneath
            # (including quotas info). See kinto/views/collection.
            return
        else:
            storage.update(
                parent_id=collection_uri,
                resource_name=QUOTA_RESOURCE_NAME,
                object_id=COLLECTION_QUOTA_OBJECT_ID,
                obj=collection_info,
            )
