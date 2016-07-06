from kinto.core import resource, utils
from kinto.core.events import ResourceChanged, ACTIONS
from pyramid.events import subscriber
from kinto.authorization import BucketRouteFactory


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

    def get_parent_id(self, request):
        # Buckets are not isolated by user, unlike Kinto-Core resources.
        return ''


@subscriber(ResourceChanged,
            for_resources=('bucket',),
            for_actions=(ACTIONS.DELETE,))
def on_buckets_deleted(event):
    """Some buckets were deleted, delete sub-resources.
    """
    storage = event.request.registry.storage

    for change in event.impacted_records:
        bucket = change['old']
        parent_id = utils.instance_uri(event.request, 'bucket',
                                       id=bucket['id'])

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
            parent_id = utils.instance_uri(event.request, 'collection',
                                           bucket_id=bucket['id'],
                                           id=collection['id'])

            storage.delete_all(collection_id='record',
                               parent_id=parent_id,
                               with_deleted=False)
            storage.purge_deleted(collection_id='record',
                                  parent_id=parent_id)
