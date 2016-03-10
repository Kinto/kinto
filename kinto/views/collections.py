import colander
import jsonschema
from cliquet import resource
from cliquet.events import ResourceChanged, ACTIONS
from jsonschema import exceptions as jsonschema_exceptions
from pyramid.events import subscriber

from kinto.views import NameGenerator


class JSONSchemaMapping(colander.SchemaNode):
    def schema_type(self, **kw):
        return colander.Mapping(unknown='preserve')

    def deserialize(self, cstruct=colander.null):
        # Start by deserializing a simple mapping.
        validated = super(JSONSchemaMapping, self).deserialize(cstruct)

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

    class Options:
        preserve_unknown = True


@resource.register(name='collection',
                   collection_methods=('GET', 'POST', 'DELETE'),
                   collection_path='/buckets/{{bucket_id}}/collections',
                   record_path='/buckets/{{bucket_id}}/collections/{{id}}')
class Collection(resource.ShareableResource):
    mapping = CollectionSchema()
    permissions = ('read', 'write', 'record:create')

    def __init__(self, *args, **kwargs):
        super(Collection, self).__init__(*args, **kwargs)
        self.model.id_generator = NameGenerator()

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        parent_id = '/buckets/%s' % bucket_id
        return parent_id


@subscriber(ResourceChanged,
            for_resources=('collection',),
            for_actions=(ACTIONS.DELETE,))
def on_collections_deleted(event):
    """Some collections were deleted, delete records.
    """
    storage = event.request.registry.storage

    for change in event.impacted_records:
        collection = change['old']
        parent_id = '/buckets/%s/collections/%s' % (event.payload['bucket_id'],
                                                    collection['id'])
        storage.delete_all(collection_id='record',
                           parent_id=parent_id,
                           with_deleted=False)
        storage.purge_deleted(collection_id='record',
                              parent_id=parent_id)
