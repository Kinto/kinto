from cliquet import resource

from kinto.views import NameGenerator


collections_options = {
    'collection_methods': ('GET',),
    'collection_path': "/buckets/{{bucket_id}}/collections",
    'record_path': "/buckets/{{bucket_id}}/collections/{{id}}"
}


@resource.register(name="collection", **collections_options)
class Collection(resource.BaseResource):

    def __init__(self, *args, **kwargs):
        super(Collection, self).__init__(*args, **kwargs)
        parent_id = '/buckets/{bucket_id}'.format(**self.request.matchdict)
        self.collection.parent_id = parent_id
        self.collection.id_generator = NameGenerator()
