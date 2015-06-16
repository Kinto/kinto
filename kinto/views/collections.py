from cliquet import resource

from kinto.views import NameGenerator, object_exists_or_404


@resource.register(name='collection',
                   collection_methods=('GET',),
                   collection_path='/buckets/{{bucket_id}}/collections',
                   record_path='/buckets/{{bucket_id}}/collections/{{id}}')
class Collection(resource.ProtectedResource):
    permissions = ('read', 'write', 'record:create')

    def __init__(self, *args, **kwargs):
        super(Collection, self).__init__(*args, **kwargs)

        bucket_id = self.request.matchdict['bucket_id']
        object_exists_or_404(self.request,
                             collection_id='bucket',
                             object_id=bucket_id)

        parent_id = '/buckets/%s' % bucket_id
        self.collection.parent_id = parent_id
        self.collection.id_generator = NameGenerator()

    def delete(self):
        result = super(Collection, self).delete()

        # Delete records.
        storage = self.collection.storage
        parent_id = '%s/collections/%s' % (self.collection.parent_id,
                                           self.record_id)
        storage.delete_all(collection_id='record', parent_id=parent_id)

        return result
