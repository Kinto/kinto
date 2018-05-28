import colander
from pyramid.events import subscriber
from pyramid.settings import asbool

from kinto.core import resource, utils
from kinto.core.errors import raise_invalid
from kinto.views import object_exists_or_404
from kinto.core.events import ResourceChanged, ACTIONS
from kinto.schema_validation import validate_schema, ValidationError, JSONSchemaMapping


class CollectionSchema(resource.ResourceSchema):
    schema = JSONSchemaMapping(missing=colander.drop)
    cache_expires = colander.SchemaNode(colander.Int(), missing=colander.drop)


@resource.register(name='collection',
                   collection_path='/buckets/{{bucket_id}}/collections',
                   record_path='/buckets/{{bucket_id}}/collections/{{id}}')
class Collection(resource.ShareableResource):
    schema = CollectionSchema
    permissions = ('read', 'write', 'record:create')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        buckets = self.request.bound_data.setdefault('buckets', {})
        bucket_uri = utils.instance_uri(self.request, 'bucket', id=self.bucket_id)
        if bucket_uri not in buckets:
            bucket = object_exists_or_404(self.request,
                                          collection_id='bucket',
                                          parent_id='',
                                          object_id=self.bucket_id)
            buckets[bucket_uri] = bucket
        self._bucket = buckets[bucket_uri]

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        parent_id = utils.instance_uri(request, 'bucket', id=self.bucket_id)
        return parent_id

    def process_record(self, new, old=None):
        """Additional collection schema validation from bucket, if any."""
        new = super().process_record(new, old)

        settings = self.request.registry.settings
        schema_validation = 'experimental_collection_schema_validation'
        if not asbool(settings.get(schema_validation)) or 'collection:schema' not in self._bucket:
            return new

        schema = self._bucket['collection:schema']

        # Remove internal and auto-assigned fields.
        internal_fields = (self.model.id_field,
                           self.model.modified_field,
                           self.model.permissions_field)
        data = {f: v for f, v in new.items() if f not in internal_fields}

        # Validate or fail with 400.
        try:
            validate_schema(data, schema, ignore_fields=internal_fields)
        except ValidationError as e:
            raise_invalid(self.request, name=e.field, description=e.message)

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
