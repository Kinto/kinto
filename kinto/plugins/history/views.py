import colander

from kinto.core import resource
from kinto.core.utils import instance_uri


class HistorySchema(resource.ResourceSchema):
    user_id = colander.SchemaNode(colander.String())
    uri = colander.SchemaNode(colander.String())
    action = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    bucket_id = colander.SchemaNode(colander.String())
    collection_id = colander.SchemaNode(colander.String())
    group_id = colander.SchemaNode(colander.String())
    record_id = colander.SchemaNode(colander.String())
    target = colander.SchemaNode(colander.Mapping())

    class Options:
        preserve_unknown = False


@resource.register(name='history',
                   collection_path='/buckets/{{bucket_id}}/history',
                   record_path=None,
                   collection_methods=('GET',))
class History(resource.ShareableResource):

    mapping = HistorySchema()

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        return instance_uri(request, 'bucket', id=self.bucket_id)
