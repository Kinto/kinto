import colander
from pyramid.events import subscriber

from kinto.core import resource, utils
from kinto.core.events import ACTIONS, ResourceChanged
from kinto.schema_validation import JSONSchemaMapping, validate_from_bucket_schema_or_400


class CollectionSchema(resource.ResourceSchema):
    schema = JSONSchemaMapping(missing=colander.drop)
    cache_expires = colander.SchemaNode(colander.Int(), missing=colander.drop)


@resource.register(
    name="collection",
    plural_path="/buckets/{{bucket_id}}/collections",
    object_path="/buckets/{{bucket_id}}/collections/{{id}}",
)
class Collection(resource.Resource):
    schema = CollectionSchema
    permissions = ("read", "write", "record:create")

    def get_parent_id(self, request):
        bucket_id = request.matchdict["bucket_id"]
        parent_id = utils.instance_uri(request, "bucket", id=bucket_id)
        return parent_id

    def process_object(self, new, old=None):
        """Additional collection schema validation from bucket, if any."""
        new = super().process_object(new, old)

        # Remove internal and auto-assigned fields.
        internal_fields = (self.model.modified_field, self.model.permissions_field)
        validate_from_bucket_schema_or_400(
            new,
            resource_name="collection",
            request=self.request,
            ignore_fields=internal_fields,
            id_field=self.model.id_field,
        )
        return new


@subscriber(ResourceChanged, for_resources=("collection",), for_actions=(ACTIONS.DELETE,))
def on_collections_deleted(event):
    """Some collections were deleted, delete records."""
    storage = event.request.registry.storage
    permission = event.request.registry.permission

    for change in event.impacted_objects:
        collection = change["old"]
        bucket_id = event.payload["bucket_id"]
        parent_id = utils.instance_uri(
            event.request, "collection", bucket_id=bucket_id, id=collection["id"]
        )
        storage.delete_all(resource_name=None, parent_id=parent_id, with_deleted=False)
        storage.purge_deleted(resource_name=None, parent_id=parent_id)
        permission.delete_object_permissions(parent_id + "/*")
