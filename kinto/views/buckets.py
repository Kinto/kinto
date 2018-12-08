import colander
from pyramid.events import subscriber

from kinto.schema_validation import JSONSchemaMapping
from kinto.core import resource
from kinto.core.utils import instance_uri
from kinto.core.events import ResourceChanged, ACTIONS


class BucketSchema(resource.ResourceSchema):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["collection:schema"] = JSONSchemaMapping(missing=colander.drop)
        self["group:schema"] = JSONSchemaMapping(missing=colander.drop)
        self["record:schema"] = JSONSchemaMapping(missing=colander.drop)


@resource.register(name="bucket", plural_path="/buckets", object_path="/buckets/{{id}}")
class Bucket(resource.Resource):
    schema = BucketSchema
    permissions = ("read", "write", "collection:create", "group:create")

    def get_parent_id(self, request):
        # Buckets are not isolated by user, unlike Kinto-Core resources.
        return ""


@subscriber(ResourceChanged, for_resources=("bucket",), for_actions=(ACTIONS.DELETE,))
def on_buckets_deleted(event):
    """Some buckets were deleted, delete sub-resources.
    """
    storage = event.request.registry.storage
    permission = event.request.registry.permission

    for change in event.impacted_objects:
        bucket = change["old"]
        bucket_uri = instance_uri(event.request, "bucket", id=bucket["id"])

        # Delete everything with current parent id (eg. collections, groups)
        # and descending children objects (eg. records).
        for pattern in (bucket_uri, bucket_uri + "/*"):
            storage.delete_all(parent_id=pattern, resource_name=None, with_deleted=False)
            # Remove remaining tombstones too.
            storage.purge_deleted(parent_id=pattern, resource_name=None)
            # Remove related permissions
            permission.delete_object_permissions(pattern)
