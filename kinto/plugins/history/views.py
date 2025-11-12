import colander
from pyramid.httpexceptions import HTTPForbidden

from kinto.core import Service, resource, utils
from kinto.core.resource.viewset import ViewSet
from kinto.core.storage import Filter, Sort
from kinto.core.utils import instance_uri


class HistorySchema(resource.ResourceSchema):
    user_id = colander.SchemaNode(colander.String())
    uri = colander.SchemaNode(colander.String())
    action = colander.SchemaNode(colander.String())
    date = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    bucket_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    collection_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    group_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    record_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    target = colander.SchemaNode(colander.Mapping())

    class Options:
        preserve_unknown = False


# Add custom OpenAPI tags/operation ids
plural_get_arguments = getattr(ViewSet, "plural_get_arguments", {})
plural_delete_arguments = getattr(ViewSet, "plural_delete_arguments", {})

get_history_arguments = {
    "tags": ["History"],
    "operation_id": "get_history",
    **plural_get_arguments,
}
delete_history_arguments = {
    "tags": ["History"],
    "operation_id": "delete_history",
    **plural_delete_arguments,
}


@resource.register(
    name="history",
    plural_path="/buckets/{{bucket_id}}/history",
    object_path=None,
    plural_methods=("GET", "DELETE"),
    default_arguments={"tags": ["History"], **ViewSet.default_arguments},
    plural_get_arguments=get_history_arguments,
    plural_delete_arguments=delete_history_arguments,
)
class History(resource.Resource):
    schema = HistorySchema

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict["bucket_id"]
        return instance_uri(request, "bucket", id=self.bucket_id)

    def _extract_filters(self):
        filters = super()._extract_filters()
        filters_str_id = []
        for filt in filters:
            if filt.field in ("record_id", "collection_id", "bucket_id"):
                if isinstance(filt.value, int):
                    filt = Filter(filt.field, str(filt.value), filt.operator)
            filters_str_id.append(filt)

        return filters_str_id


snapshot = Service(
    name="history_snapshot",
    path="/buckets/{bucket_id}/snapshot/collections/{collection_id}@{timestamp}",
    description="Reconstruct collection at given timestamp",
)


def timestamp_validator(request, **kwargs):
    """
    Validates that the timestamp is an integer.
    """
    timestamp = request.matchdict["timestamp"]
    try:
        if int(timestamp) < 0:
            raise ValueError
    except ValueError:
        request.errors.add("path", "timestamp", "Invalid timestamp %r" % timestamp)


@snapshot.get(validators=(timestamp_validator,))
def get_snapshot(request):
    """Reconstructs the collection as it was at the given timestamp."""

    bucket_id = request.matchdict["bucket_id"]
    collection_id = request.matchdict["collection_id"]
    timestamp = int(request.matchdict["timestamp"])

    bucket_uri = instance_uri(request, "bucket", id=bucket_id)
    collection_uri = instance_uri(request, "collection", bucket_id=bucket_id, id=collection_id)

    # Check that user has read permission on the collection.
    # This is manual code, because we are outside the normal resource system.
    if not request.registry.permission.check_permission(
        request.prefixed_principals,
        [
            (bucket_uri, "read"),
            (bucket_uri, "write"),
            (collection_uri, "read"),
            (collection_uri, "write"),
        ],
    ):
        raise HTTPForbidden()

    # List all the records that have changed since the given timestamp.
    all_records = request.registry.storage.list_all(
        parent_id=collection_uri,
        resource_name="record",
        include_deleted=True,  # Include tombstones
    )

    unchanged_records = [
        r for r in all_records if r["last_modified"] <= timestamp and not r.get("deleted")
    ]
    changed_rids = [r["id"] for r in all_records if r["last_modified"] > timestamp]
    if not changed_rids:
        # No change after timestamp, return all records as-is.
        return {"data": sorted(unchanged_records, key=lambda r: r["last_modified"], reverse=True)}

    # History entries store the current version. We need to pick the most recent
    # entry before the timestamp for each record_id to obtain the records' state
    # before it was changed or deleted.
    history_entries = request.registry.storage.list_all(
        parent_id=bucket_uri,
        resource_name="history",
        filters=[
            Filter("resource_name", "record", utils.COMPARISON.EQ),
            Filter("collection_id", collection_id, utils.COMPARISON.EQ),
            Filter("record_id", changed_rids, utils.COMPARISON.IN),
            Filter("target.data.last_modified", timestamp, utils.COMPARISON.MAX),
        ],
        sorting=[Sort("last_modified", -1)],  # Most recent first
        # TODO: add storage option to keep only the latest entry per record_id
    )

    most_recent_entry = {}
    for entry in history_entries:
        rid = entry["record_id"]
        if rid not in most_recent_entry:
            most_recent_entry[rid] = entry

    # Records created after the timestamp (not existing in history) should not appear.
    # Records deleted or updated after the timestamp should be reverted to their most recent
    # version before the timestamp.
    result_records = unchanged_records
    for rid in changed_rids:
        if rid not in most_recent_entry:
            # Record was created after the timestamp, skip it.
            continue
        history_entry = most_recent_entry[rid]
        result_records.append(history_entry["target"]["data"])

    return {"data": sorted(result_records, key=lambda r: r["last_modified"], reverse=True)}
