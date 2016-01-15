from cliquet import resource
from kinto.views import NameGenerator


@resource.register(name='bucket',
                   collection_methods=('GET', 'POST'),
                   collection_path='/buckets',
                   record_path='/buckets/{{id}}')
class Bucket(resource.ProtectedResource):
    permissions = ('read', 'write', 'collection:create', 'group:create')

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        self.model.id_generator = NameGenerator()

    def get_parent_id(self, request):
        # Buckets are not isolated by user, unlike Cliquet resources.
        return ''

    def delete(self):
        result = super(Bucket, self).delete()

        # Delete groups.
        storage = self.model.storage
        parent_id = '/buckets/%s' % self.record_id
        storage.delete_all(collection_id='group',
                           parent_id=parent_id,
                           with_deleted=False)
        storage.purge_deleted(collection_id='group',
                              parent_id=parent_id)

        # Delete collections.
        deleted = storage.delete_all(collection_id='collection',
                                     parent_id=parent_id,
                                     with_deleted=False)
        storage.purge_deleted(collection_id='collection',
                              parent_id=parent_id)

        # Delete records.
        id_field = self.model.id_field
        for collection in deleted:
            parent_id = '/buckets/%s/collections/%s' % (self.record_id,
                                                        collection[id_field])
            storage.delete_all(collection_id='record',
                               parent_id=parent_id,
                               with_deleted=False)
            storage.purge_deleted(collection_id='record', parent_id=parent_id)

        return result
