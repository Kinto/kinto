import jsonschema
from kinto.core import resource, utils
from kinto.core.errors import raise_invalid
from jsonschema import exceptions as jsonschema_exceptions
from pyramid.security import Authenticated
from pyramid.settings import asbool

from kinto.views import object_exists_or_404


_parent_path = '/buckets/{{bucket_id}}/collections/{{collection_id}}'


@resource.register(name='record',
                   collection_path=_parent_path + '/records',
                   record_path=_parent_path + '/records/{{id}}')
class Record(resource.ShareableResource):

    schema_field = 'schema'

    def __init__(self, request, **kwargs):
        # Before all, first check that the parent collection exists.
        # Check if already fetched before (in batch).
        collections = request.bound_data.setdefault('collections', {})
        collection_uri = self.get_parent_id(request)
        if collection_uri not in collections:
            # Unknown yet, fetch from storage.
            collection_parent_id = utils.instance_uri(request, 'bucket',
                                                      id=self.bucket_id)
            collection = object_exists_or_404(request,
                                              collection_id='collection',
                                              parent_id=collection_parent_id,
                                              object_id=self.collection_id)
            collections[collection_uri] = collection

        super().__init__(request, **kwargs)
        self._collection = collections[collection_uri]

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        self.collection_id = request.matchdict['collection_id']
        return utils.instance_uri(request, 'collection',
                                  bucket_id=self.bucket_id,
                                  id=self.collection_id)

    def process_record(self, new, old=None):
        """Validate records against collection schema, if any."""
        new = super().process_record(new, old)

        schema = self._collection.get('schema')
        settings = self.request.registry.settings
        schema_validation = 'experimental_collection_schema_validation'
        if not schema or not asbool(settings.get(schema_validation)):
            return new

        # Remove internal and auto-assigned fields from schema and record.
        internal_fields = (self.model.id_field,
                           self.model.modified_field,
                           self.schema_field,
                           self.model.permissions_field)
        required_fields = [f for f in schema.get('required', []) if f not in internal_fields]
        if required_fields:
            schema = {**schema, 'required': required_fields}
        else:
            schema = {f: v for f, v in new.items() if f != 'required'}
        data = {f: v for f, v in new.items() if f not in internal_fields}

        # Validate or fail with 400.
        try:
            jsonschema.validate(data, schema)
        except jsonschema_exceptions.ValidationError as e:
            if e.path:
                field = e.path[-1]
            elif e.validator_value:
                field = e.validator_value[-1]
            else:
                field = e.schema_path[-1]
            raise_invalid(self.request, name=field, description=e.message)

        # Assign the schema version (collection object timestamp) to the record.
        collection_timestamp = self._collection[self.model.modified_field]
        new[self.schema_field] = collection_timestamp

        return new

    def collection_get(self):
        result = super().collection_get()
        self._handle_cache_expires(self.request.response)
        return result

    def get(self):
        result = super().get()
        self._handle_cache_expires(self.request.response)
        return result

    def _handle_cache_expires(self, response):
        """If the parent collection defines a ``cache_expires`` attribute,
        then cache-control response headers are sent.

        .. note::

            Those headers are also sent if the
            ``kinto.record_cache_expires_seconds`` setting is defined.
        """
        is_anonymous = Authenticated not in self.request.effective_principals
        if not is_anonymous:
            return

        cache_expires = self._collection.get('cache_expires')
        if cache_expires is None:
            by_bucket = '{}_record_cache_expires_seconds'.format(self.bucket_id)
            by_collection = '{}_{}_record_cache_expires_seconds'.format(
                self.bucket_id, self.collection_id)
            settings = self.request.registry.settings
            cache_expires = settings.get(by_collection,
                                         settings.get(by_bucket))

        if cache_expires is not None:
            response.cache_expires(seconds=int(cache_expires))
