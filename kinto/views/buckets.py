from cliquet import resource

from kinto.views import NameGenerator


buckets_options = {
    'collection_methods': ('GET',)
}


@resource.register(name="bucket", **buckets_options)
class Bucket(resource.BaseResource):

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        self.collection.id_generator = NameGenerator()
