from cliquet import resource

from kinto.views import NameGenerator, object_exists_or_404


collections_options = {
    'collection_methods': ('GET',),
    'collection_path': "/buckets/{{bucket_id}}/collections",
    'record_path': "/buckets/{{bucket_id}}/collections/{{id}}"
}


@resource.register(name="collection", **collections_options)
class Collection(resource.BaseResource):

    def __init__(self, *args, **kwargs):
        super(Collection, self).__init__(*args, **kwargs)

        bucket_id = self.request.matchdict['bucket_id']
        object_exists_or_404(self.request,
                             collection_id='bucket',
                             object_id=bucket_id)

        parent_id = '/buckets/%s' % bucket_id
        self.collection.parent_id = parent_id
        self.collection.id_generator = NameGenerator()
