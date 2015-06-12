from cliquet import resource

from kinto.views import NameGenerator


@resource.register(name='bucket',
                   collection_methods=('GET',),
                   collection_path='/buckets',
                   record_path='/buckets/{{id}}')
class Bucket(resource.ProtectedResource):
    permissions = ('read', 'write', 'collection:create', 'group:create')

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        # Buckets are not isolated by user, unlike Cliquet resources.
        self.collection.parent_id = ''
        self.collection.id_generator = NameGenerator()

    def delete(self):
        result = super(Bucket, self).delete()

        # Delete groups.
        storage = self.collection.storage
        parent_id = '/buckets/%s' % self.record_id
        storage.delete_all(collection_id='group', parent_id=parent_id)

        # Delete collections.
        deleted = storage.delete_all(collection_id='collection',
                                     parent_id=parent_id)

        # Delete records.
        id_field = self.collection.id_field
        for collection in deleted:
            parent_id = '/buckets/%s/collections/%s' % (self.record_id,
                                                        collection[id_field])
            storage.delete_all(collection_id='record', parent_id=parent_id)

        return result
