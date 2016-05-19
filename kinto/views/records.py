import copy

import jsonschema
from kinto.core import resource
from kinto.core.errors import raise_invalid
from jsonschema import exceptions as jsonschema_exceptions
from pyramid.security import Authenticated
from pyramid.settings import asbool

from kinto.views import object_exists_or_404


class RecordSchema(resource.ResourceSchema):
    class Options:
        preserve_unknown = True


_parent_path = '/buckets/{{bucket_id}}/collections/{{collection_id}}'


@resource.register(name='record',
                   collection_path=_parent_path + '/records',
                   record_path=_parent_path + '/records/{{id}}')
class Record(resource.ShareableResource):

    mapping = RecordSchema()
    schema_field = 'schema'

    def __init__(self, *args, **kwargs):
        super(Record, self).__init__(*args, **kwargs)

        # Check if already fetched before (in batch).
        collections = self.request.bound_data.setdefault('collections', {})
        collection_uri = self.get_parent_id(self.request)
        if collection_uri not in collections:
            # Unknown yet, fetch from storage.
            collection_parent_id = '/buckets/%s' % self.bucket_id
            collection = object_exists_or_404(self.request,
                                              collection_id='collection',
                                              parent_id=collection_parent_id,
                                              object_id=self.collection_id)
            collections[collection_uri] = collection

        self._collection = collections[collection_uri]

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        self.collection_id = request.matchdict['collection_id']
        return '/buckets/%s/collections/%s' % (self.bucket_id,
                                               self.collection_id)

    def is_known_field(self, field_name):
        """Without schema, any field is considered as known."""
        return True

    def process_record(self, new, old=None):
        """Validate records against collection schema, if any."""
        new = super(Record, self).process_record(new, old)

        schema = self._collection.get('schema')
        settings = self.request.registry.settings
        schema_validation = 'experimental_collection_schema_validation'
        if not schema or not asbool(settings.get(schema_validation)):
            return new

        collection_timestamp = self._collection[self.model.modified_field]

        try:
            stripped = copy.deepcopy(new)
            stripped.pop(self.model.id_field, None)
            stripped.pop(self.model.modified_field, None)
            stripped.pop(self.model.permissions_field, None)
            stripped.pop(self.schema_field, None)
            jsonschema.validate(stripped, schema)
        except jsonschema_exceptions.ValidationError as e:
            try:
                field = e.path.pop() if e.path else e.validator_value.pop()
            except AttributeError:
                field = None
            raise_invalid(self.request, name=field, description=e.message)

        new[self.schema_field] = collection_timestamp
        return new

    def collection_get(self):
        result = super(Record, self).collection_get()
        self._handle_cache_expires(self.request.response)
        return result

    def get(self):
        result = super(Record, self).get()
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
            by_bucket = '%s_record_cache_expires_seconds' % (self.bucket_id)
            by_collection = '%s_%s_record_cache_expires_seconds' % (
                self.bucket_id, self.collection_id)
            settings = self.request.registry.settings
            cache_expires = settings.get(by_collection,
                                         settings.get(by_bucket))

        if cache_expires is not None:
            response.cache_expires(seconds=int(cache_expires))
