from cliquet import resource, schema

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

        parent_id = '/buckets/%s/collections/%s' % (bucket_id, collection_id)
        self.collection.parent_id = parent_id

    def is_known_field(self, field_name):
        """Without schema, any field is considered as known."""
        return True
