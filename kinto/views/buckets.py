from cliquet import resource

from kinto.views import NameGenerator


buckets_options = {
    'collection_methods': ('GET',)
}


@resource.register(name="bucket", **buckets_options)
class Bucket(resource.BaseResource):

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        # Buckets are not isolated by user, like Cliquet resources.
        self.collection.parent_id = ''
        self.collection.id_generator = NameGenerator()
