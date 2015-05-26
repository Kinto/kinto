import jsonschema
from cliquet import resource, schema
from cliquet.errors import raise_invalid
from jsonschema import exceptions as jsonschema_exceptions
from pyramid import httpexceptions

from kinto.views import schema as views_schema

from kinto.views import object_exists_or_404


class RecordSchema(schema.ResourceSchema):
    class Options():
        preserve_unknown = True


_parent_path = '/buckets/{{bucket_id}}/collections/{{collection_id}}'


@resource.register(name='record',
                   collection_path=_parent_path + '/records',
                   record_path=_parent_path + '/records/{{id}}')
class Record(resource.ProtectedResource):

    mapping = RecordSchema()
    schema_field = 'schema'

    def __init__(self, *args, **kwargs):
        super(Record, self).__init__(*args, **kwargs)

        bucket_id = self.request.matchdict['bucket_id']
        object_exists_or_404(self.request,
                             collection_id='bucket',
                             object_id=bucket_id)

        collection_id = self.request.matchdict['collection_id']
        object_exists_or_404(self.request,
                             collection_id='collection',
                             parent_id='/buckets/%s' % bucket_id,
                             object_id=collection_id)

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        collection_id = request.matchdict['collection_id']
        return '/buckets/%s/collections/%s' % (bucket_id, collection_id)

    def is_known_field(self, field_name):
        """Without schema, any field is considered as known."""
        return True

    def process_record(self, new, old=None):
        """Validate records against collection schema, if any."""
        schema = self._get_collection_schema()
        if schema is None:
            return new

        try:
            jsonschema.validate(new, schema)
            # Save schema timestamp as record schema version.
            new[self.schema_field] = schema[self.collection.modified_field]
        except jsonschema_exceptions.ValidationError as e:
            field = e.path.pop() if e.path else e.validator_value.pop()
            raise_invalid(self.request, name=field, description=e.message)

        return new

    def _get_collection_schema(self):
        """Return the JSON schema of the collection matched, or ``None``
        if not any was defined.
        """
        try:
            return views_schema.Schema(self.request).get()['data']
        except httpexceptions.HTTPNotFound:
            pass
