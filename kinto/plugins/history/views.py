import colander

from kinto.core import resource


class HistorySchema(resource.ResourceSchema):
    userid = colander.SchemaNode(colander.String())
    uri = colander.SchemaNode(colander.String())
    action = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    # XXX
    # bucket_id
    # collection_id
    # group_id
    # record_id
    # target : object(data, permissions)


@resource.register(name='history',
                   collection_path='/buckets/{{bucket_id}}/history',
                   collection_methods=('GET',))
class History(resource.ShareableResource):

    mapping = HistorySchema()

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        return '/buckets/%s' % self.bucket_id
