from kinto.core import resource
from kinto.core.events import ResourceChanged, ACTIONS
from pyramid.events import subscriber
from kinto.authorization import BucketRouteFactory
from kinto.views import NameGenerator


class BucketSchema(resource.ResourceSchema):
    class Options:
        preserve_unknown = True


@resource.register(name='bucket',
                   collection_path='/buckets',
                   record_path='/buckets/{{id}}',
                   factory=BucketRouteFactory)
class Bucket(resource.ShareableResource):
    mapping = BucketSchema()
    permissions = ('read', 'write', 'collection:create', 'group:create')

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        self.model.id_generator = NameGenerator()

    def get_parent_id(self, request):
        # Buckets are not isolated by user, unlike Kinto-Core resources.
        return ''

    def is_known_field(self, field_name):
        """Without schema, any field is considered as known."""
        return True


@subscriber(ResourceChanged,
            for_resources=('bucket',),
            for_actions=(ACTIONS.DELETE,))
def on_buckets_deleted(event):
    """Some buckets were deleted, delete sub-resources.
    """
    storage = event.request.registry.storage

    for change in event.impacted_records:
        bucket = change['old']
        parent_id = '/buckets/%s' % bucket['id']

        # Delete groups.
        storage.delete_all(collection_id='group',
                           parent_id=parent_id,
                           with_deleted=False)
        storage.purge_deleted(collection_id='group',
                              parent_id=parent_id)

        # Delete collections.
        deleted_collections = storage.delete_all(collection_id='collection',
                                                 parent_id=parent_id,
                                                 with_deleted=False)
        storage.purge_deleted(collection_id='collection',
                              parent_id=parent_id)

        # Delete records.
        for collection in deleted_collections:
            parent_id = '/buckets/%s/collections/%s' % (bucket['id'],
                                                        collection['id'])
            storage.delete_all(collection_id='record',
                               parent_id=parent_id,
                               with_deleted=False)
            storage.purge_deleted(collection_id='record',
                                  parent_id=parent_id)
