import colander

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import resource, Service
from kinto.core.utils import instance_uri
from kinto.core.storage import Filter, Sort
from kinto.core.resource.viewset import ViewSet
from kinto.core.utils import COMPARISON


class HistorySchema(resource.ResourceSchema):
    user_id = colander.SchemaNode(colander.String())
    uri = colander.SchemaNode(colander.String())
    action = colander.SchemaNode(colander.String())
    date = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    bucket_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    collection_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    group_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    record_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    target = colander.SchemaNode(colander.Mapping())

    class Options:
        preserve_unknown = False


# Add custom OpenAPI tags/operation ids
collection_get_arguments = getattr(ViewSet, "collection_get_arguments", {})
collection_delete_arguments = getattr(ViewSet, "collection_delete_arguments", {})

get_history_arguments = {'tags': ['History'], 'operation_id': 'get_history',
                         **collection_get_arguments}
delete_history_arguments = {'tags': ['History'], 'operation_id': 'delete_history',
                            **collection_delete_arguments}


@resource.register(name='history',
                   collection_path='/buckets/{{bucket_id}}/history',
                   record_path=None,
                   collection_methods=('GET', 'DELETE'),
                   default_arguments={'tags': ['History']},
                   collection_get_arguments=get_history_arguments,
                   collection_delete_arguments=delete_history_arguments)
class History(resource.ShareableResource):

    schema = HistorySchema

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        return instance_uri(request, 'bucket', id=self.bucket_id)

    def _extract_filters(self):
        filters = super()._extract_filters()
        filters_str_id = []
        for filt in filters:
            if filt.field in ('record_id', 'collection_id', 'bucket_id'):
                if isinstance(filt.value, int):
                    filt = Filter(filt.field, str(filt.value), filt.operator)
            filters_str_id.append(filt)

        return filters_str_id


version_view = Service(name='version_view',
                       description='Handle retrieving object from the past.',
                       path='{subpath:.*}/version/{last_modified:[0-9]{13}}')


@version_view.get(permission=NO_PERMISSION_REQUIRED)
def get_version_view(request):
    last_modified = int(request.matchdict['last_modified'])
    subpath = '/{}'.format(request.matchdict['subpath'])

    if not subpath.startswith('/buckets'):
        raise httpexceptions.HTTPNotFound()

    bucket_id = request.matchdict['subpath'].split('/', 2)[1]
    bucket_uri = '/buckets/{}'.format(bucket_id)

    is_collection = [True for collection_type in ['collections', 'groups', 'records']
                     if subpath.endswith('/{}'.format(collection_type))]

    # Handle collections
    if is_collection:
        return handle_version_on_collections(request, last_modified, bucket_uri)

    # Handle records
    return handle_version_on_records(request, last_modified, bucket_uri)


def handle_version_on_collections(request, last_modified, bucket_uri):
    parent_id = '/{}/*'.format(request.matchdict['subpath'])
    resource_name = 'collection'

    # We want to get the record at a certain time.
    filters = [Filter('target.data.last_modified', last_modified, COMPARISON.MAX),
               Filter('resource_name', resource_name, COMPARISON.EQ),
               Filter('uri', parent_id, COMPARISON.LIKE)]
    sorting = [Sort('last_modified', -1)]

    records, count = request.registry.storage.get_all(
        collection_id='history', parent_id=bucket_uri,
        filters=filters, sorting=sorting)

    return {"data": [record['target']['data'] for record in records]}


def handle_version_on_records(request, last_modified, bucket_uri):
    parent_id = '/{}'.format(request.matchdict['subpath'])

    # We want to get the record at a certain time.
    filters = [Filter('target.data.last_modified', last_modified, COMPARISON.MAX),
               Filter('uri', parent_id, COMPARISON.EQ)]
    sorting = [Sort('last_modified', -1)]

    records, count = request.registry.storage.get_all(
        collection_id='history', parent_id=bucket_uri,
        filters=filters, sorting=sorting, limit=1)
    if count > 0:
        return {"data": records[0]['target']['data']}
    raise httpexceptions.HTTPNotFound()
