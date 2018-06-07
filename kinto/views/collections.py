import colander
from pyramid.events import subscriber

from kinto.core import resource, utils
from kinto.core.events import ResourceChanged, ACTIONS
from kinto.schema_validation import validate_from_bucket_schema_or_400, JSONSchemaMapping


class CollectionSchema(resource.ResourceSchema):
    schema = JSONSchemaMapping(missing=colander.drop)
    cache_expires = colander.SchemaNode(colander.Int(), missing=colander.drop)


@resource.register(name='collection',
                   collection_path='/buckets/{{bucket_id}}/collections',
                   record_path='/buckets/{{bucket_id}}/collections/{{id}}')
class Collection(resource.ShareableResource):
    schema = CollectionSchema
    permissions = ('read', 'write', 'record:create')

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        parent_id = utils.instance_uri(request, 'bucket', id=bucket_id)
        return parent_id

    def process_record(self, new, old=None):
        """Additional collection schema validation from bucket, if any."""
        new = super().process_record(new, old)

        # Remove internal and auto-assigned fields.
        internal_fields = (self.model.id_field,
                           self.model.modified_field,
                           self.model.permissions_field)
        validate_from_bucket_schema_or_400(new, resource_name="collection", request=self.request,
                                           ignore_fields=internal_fields)
        return new


@subscriber(ResourceChanged,
            for_resources=('collection',),
            for_actions=(ACTIONS.DELETE,))
def on_collections_deleted(event):
    """Some collections were deleted, delete records.
    """
    storage = event.request.registry.storage
    permission = event.request.registry.permission

    for change in event.impacted_records:
        collection = change['old']
        bucket_id = event.payload['bucket_id']
        parent_id = utils.instance_uri(event.request, 'collection',
                                       bucket_id=bucket_id,
                                       id=collection['id'])
        storage.delete_all(collection_id=None,
                           parent_id=parent_id,
                           with_deleted=False)
        storage.purge_deleted(collection_id=None,
                              parent_id=parent_id)
        permission.delete_object_permissions(parent_id)
