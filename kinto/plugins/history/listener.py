import logging
from datetime import datetime, timezone

from pyramid.settings import asbool, aslist

from kinto.core.storage import Filter, Sort
from kinto.core.utils import COMPARISON, instance_uri


logger = logging.getLogger(__name__)


def on_resource_changed(event):
    """
    Everytime an object is created/changed/deleted, we create an entry in the
    ``history`` resource. The entries are served as read-only in the
    :mod:`kinto.plugins.history.views` module.
    """
    payload = event.payload
    resource_name = payload["resource_name"]
    event_uri = payload["uri"]
    user_id = payload["user_id"]

    storage = event.request.registry.storage
    permission = event.request.registry.permission
    settings = event.request.registry.settings

    excluded_user_ids = aslist(settings.get("history.exclude_user_ids", ""))
    if user_id in excluded_user_ids:
        logger.info(f"History entries for user {user_id!r} are disabled in config")
        return

    trim_history_max = int(settings.get("history.auto_trim_max_count", "-1"))
    is_trim_enabled = trim_history_max > 0
    trim_user_ids = aslist(settings.get("history.auto_trim_user_ids", ""))
    is_trim_by_user_enabled = len(trim_user_ids) > 0

    bucket_id = None
    bucket_uri = None
    collection_uri = None

    excluded_resources = aslist(settings.get("history.exclude_resources", ""))

    targets = []
    for impacted in event.impacted_objects:
        target = impacted["new"]
        obj_id = target["id"]

        try:
            bucket_id = payload["bucket_id"]
        except KeyError:
            # e.g. DELETE /buckets
            bucket_id = obj_id
        bucket_uri = instance_uri(event.request, "bucket", id=bucket_id)

        if bucket_uri in excluded_resources:
            logger.info(f"History entries for bucket {bucket_uri!r} are disabled in config")
            continue

        if "collection_id" in payload:
            collection_id = payload["collection_id"]
            collection_uri = instance_uri(
                event.request, "collection", bucket_id=bucket_id, id=collection_id
            )
            if collection_uri in excluded_resources:
                logger.info(
                    f"History entries for collection {collection_uri!r} are disabled in config"
                )
                continue

        # On POST .../records, the URI does not contain the newly created
        # record id.
        parts = event_uri.split("/")
        if resource_name in parts[-1]:
            parts.append(obj_id)
        else:
            # Make sure the id is correct on grouped events.
            parts[-1] = obj_id
        uri = "/".join(parts)

        if uri in excluded_resources:
            logger.info(f"History entries for record {uri!r} are disabled in config")
            continue

        targets.append((uri, target))

    if not targets:
        return  # Nothing to do.

    # Prepare a list of object ids to be fetched from permission backend,
    # and fetch them all at once. Use a mapping for later convenience.
    all_perms_objects_ids = [oid for (oid, _) in targets]
    all_perms_objects_ids.append(bucket_uri)
    if collection_uri is not None:
        all_perms_objects_ids.append(collection_uri)
    all_perms_objects_ids = list(set(all_perms_objects_ids))
    all_permissions = permission.get_objects_permissions(all_perms_objects_ids)
    perms_by_object_id = dict(zip(all_perms_objects_ids, all_permissions))

    bucket_perms = perms_by_object_id[bucket_uri]
    collection_perms = {}
    if collection_uri is not None:
        collection_perms = perms_by_object_id[collection_uri]

    # The principals allowed to read the bucket and collection.
    # (Note: ``write`` means ``read``)
    read_principals = set(bucket_perms.get("read", []))
    read_principals.update(bucket_perms.get("write", []))
    read_principals.update(collection_perms.get("read", []))
    read_principals.update(collection_perms.get("write", []))

    # Create a history entry for each impacted object.
    for uri, target in targets:
        obj_id = target["id"]
        # Prepare the history entry attributes.
        perms = {k: list(v) for k, v in perms_by_object_id[uri].items()}
        eventattrs = dict(**payload)
        eventattrs.pop("timestamp", None)  # Already in target `last_modified`.
        eventattrs.pop("bucket_id", None)
        eventattrs[f"{resource_name}_id"] = obj_id
        eventattrs["uri"] = uri
        attrs = dict(
            date=datetime.now(timezone.utc).isoformat(),
            target={"data": target, "permissions": perms},
            **eventattrs,
        )

        # Create an entry for the 'history' resource, whose parent_id is
        # the bucket URI (c.f. views.py).
        # Note: this will be rolledback if the transaction is rolledback.
        entry = storage.create(parent_id=bucket_uri, resource_name="history", obj=attrs)

        # If enabled, we trim history by resource.
        # This means that we will only keep the last `auto_trim_max_count` history entries
        # for this same type of object (eg. `collection`, `record`).
        #
        # If trim by user is enabled, we only trim if the user matches the config
        # and we only delete the history entries of this user.
        # This means that if a user touches X different types of objects, we will keep
        # ``(X * auto_trim_max_count)`` entries.
        if is_trim_enabled and (not is_trim_by_user_enabled or user_id in trim_user_ids):
            filters = [
                Filter("resource_name", resource_name, COMPARISON.EQ),
            ]
            if is_trim_by_user_enabled:
                filters.append(Filter("user_id", user_id, COMPARISON.EQ))

            # Identify the oldest entry to keep.
            previous_entries = storage.list_all(
                parent_id=bucket_uri,
                resource_name="history",
                filters=filters,
                sorting=[Sort("last_modified", -1)],
                limit=trim_history_max + 1,
            )
            # And delete all older ones.
            if len(previous_entries) > trim_history_max:
                trim_before_timestamp = previous_entries[-1]["last_modified"]
                deleted = storage.delete_all(
                    parent_id=bucket_uri,
                    resource_name="history",
                    filters=filters
                    + [Filter("last_modified", trim_before_timestamp, COMPARISON.MAX)],
                )
                logger.info(f"Trimmed {len(deleted)} old history entries.")
            else:
                logger.info(
                    "No old history to trim for {user_id!r} on {resource_name!r} in {bucket_uri!r}."
                )
        else:
            logger.info(
                f"Trimming of old history entries is not enabled{f' for {user_id!r}.' if is_trim_enabled else '.'}"
            )

        # Without explicit permissions, the ACLs on the history entries will
        # fully depend on the inherited permission tree (eg. bucket:read, bucket:write).
        # This basically means that if user loose the permissions on the related
        # object, they also loose the permission on the history entry.
        # See https://github.com/Kinto/kinto/issues/893
        if not asbool(settings["explicit_permissions"]):
            return

        # The read permission on the newly created history entry is the union
        # of the object permissions with the one from bucket and collection.
        entry_principals = set(read_principals)
        entry_principals.update(perms.get("read", []))
        entry_principals.update(perms.get("write", []))
        entry_perms = {"read": list(entry_principals)}
        # /buckets/{id}/history is the URI for the list of history entries.
        entry_perm_id = f"/buckets/{bucket_id}/history/{entry['id']}"
        permission.replace_object_permissions(entry_perm_id, entry_perms)
