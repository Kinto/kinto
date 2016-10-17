import colander
import requests

from kinto.core import resource, Service
from kinto.core.utils import instance_uri
from kinto.core.storage import Filter
from kinto.core.errors import raise_invalid


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


class Revert(object):

    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'

    def __init__(self, request):
        self.request = request

    def revert_changes(self, history, since):
        revert_list = self.build_revert_list(history, since)
        if len(revert_list) == 0:
            raise_error(self.request, 'no history', 'there are no history records to revert after since timestamp')
        return { 'data': revert_list }

    def create_revert_operation(self, last, first, passed_since):
        rec_id = last['target']['data']['id']
        if last['action'] == self.CREATE or (not passed_since and first['action'] == self.CREATE):
            return {'action': self.DELETE, 'data':  {'id': rec_id}}
        else:
            return {'action': self.UPDATE, 'data':  first['target']['data']}

    def insert_rec_to_revert_lists(self, rec, revert_lists, passed_since):
        rec_id = rec['target']['data']['id']
        if passed_since:
            if rec_id not in revert_lists['not_paired']:
                return
            last_change = revert_lists['not_paired'].pop(rec_id)
            revert_lists['paired'].append(self.create_revert_operation(last_change, rec, passed_since))
        else:
            if rec_id in revert_lists['not_paired']:
                if rec['action'] == self.CREATE:
                    last_change = revert_lists['not_paired'].pop(rec_id)
                    revert_lists['paired'].append(self.create_revert_operation(last_change, rec, passed_since))
            elif rec['action'] == self.CREATE:
                revert_lists['paired'].append(self.create_revert_operation(rec, None, passed_since))
            else:
                revert_lists['not_paired'][rec_id] = rec

    def build_revert_list(self, history, since):
        revert_lists = {'not_paired': {}, 'paired': []}
        passed_since = False
        for rec in history['data']:
            if not passed_since and rec['last_modified'] < since:
                passed_since = True
            print passed_since
            if passed_since and len(revert_lists['not_paired']) == 0:
                break
            self.insert_rec_to_revert_lists(rec, revert_lists, passed_since)

        return revert_lists['paired']


revert_service = Service(name="revert",
                     path='/buckets/{bucket_id}/collections/{collection_id}/revert',
                     description="Revert a collection to a timestamp, "
                                 "all later records will be discarded")

def raise_error(request, name, description):
    error_details = {
        'name': name,
        'description': description,
    }
    raise_invalid(request, **error_details)

@revert_service.post()
def revert_post(request):
    bucket_id = request.matchdict['bucket_id']
    collection_id = request.matchdict['collection_id']
    if 'since' not in request.params:
        raise_error(request, 'since', 'since request parameter must be provided')
    else:
        since = int(request.params['since'])

    (host, port) = ('localhost', '8888') #(request.get_hostname(), request.get_port())
    history = requests.get('http://%s:%s/v1/buckets/default/history?collection_id=%s' 
                           % (host, port, collection_id), auth=('token', 'my-secret'))

    revert = Revert(request)
    return revert.revert_changes(history.json(),since)
    #return []
