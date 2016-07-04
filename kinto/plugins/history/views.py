from kinto.core import resource


@resource.register(name='history',
                   collection_path='/buckets/{{bucket_id}}/history',
                   collection_methods=('GET',))
class History(resource.ShareableResource):
    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        return '/buckets/%s' % self.bucket_id
