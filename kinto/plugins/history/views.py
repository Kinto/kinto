import colander

from kinto.core import resource
from kinto.core.utils import instance_uri
from kinto.core.storage import Filter


class HistorySchema(resource.ResourceSchema):
    user_id = colander.SchemaNode(colander.String())
    uri = colander.SchemaNode(colander.String())
    action = colander.SchemaNode(colander.String())
    date = colander.SchemaNode(colander.String())
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

    def _extract_filters(self, queryparams=None):
        filters = super(History, self)._extract_filters(queryparams)
        filters_str_id = []
        for filt in filters:
            if filt.field in ('record_id', 'collection_id', 'bucket_id'):
                if isinstance(filt.value, int):
                    filt = Filter(filt.field, str(filt.value), filt.operator)
            filters_str_id.append(filt)

        return filters_str_id
