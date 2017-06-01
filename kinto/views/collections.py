import colander
import jsonschema
from kinto.core import resource, utils
from kinto.core.events import ResourceChanged, ACTIONS
from jsonschema import exceptions as jsonschema_exceptions
from pyramid.events import subscriber


class JSONSchemaMapping(colander.SchemaNode):
    def schema_type(self, **kw):
        return colander.Mapping(unknown='preserve')

    def deserialize(self, cstruct=colander.null):
        # Start by deserializing a simple mapping.
        validated = super().deserialize(cstruct)

        # In case it is optional in parent schema.
        if not validated or validated in (colander.null, colander.drop):
            return validated

        try:
            jsonschema.Draft4Validator.check_schema(validated)
        except jsonschema_exceptions.SchemaError as e:
            self.raise_invalid(e.path.pop() + e.message)
        return validated


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
