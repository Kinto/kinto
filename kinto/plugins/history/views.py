import colander

from kinto.core import resource, Service
from kinto.core.utils import instance_uri
from kinto.core.storage import Filter
from kinto.core.errors import raise_invalid
from kinto.core.events import ACTIONS


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

    schema = HistorySchema

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


class Revert(resource.UserResource):

    def __init__(self, request):
        self.request = request
        self.bucket_id = request.matchdict['bucket_id']
        if 'since' not in request.params:
            raise_error(request, 'since', 'since request parameter must be provided')
        self.since = int(request.params['since'])
        filters = super(Revert, self)._extract_filters(request.params)
        filters = [s for s in filters
                                 if s.field != 'since']
        self.storage = request.registry.storage
        self.history, _ = self.storage.get_all(parent_id='/buckets/%s' % self.bucket_id,
                                               collection_id='history', filters=filters)

    def revert_changes(self):
        revert_list = self.build_revert_list()
        if len(revert_list) == 0:
            raise_error(self.request, 'no history', 'there are no history records to revert after since timestamp')
        return { 'data': revert_list }

    def create_revert_operation(self, last, first, passed_since):
        rec_id = last['target']['data']['id']
        last_is_create = last['action'] == ACTIONS.CREATE.value
        if last_is_create or (not passed_since and first['action'] == ACTIONS.CREATE.value):
            return {'action': ACTIONS.DELETE.value, 'data':  {'id': rec_id}}
        else:
            return {'action': ACTIONS.UPDATE.value, 'data':  first['target']['data']}

    def insert_rec_to_revert_lists(self, rec, revert_lists, passed_since):
        rec_id = rec['target']['data']['id']
        if passed_since:
            if rec_id not in revert_lists['not_paired']:
                return
            last_change = revert_lists['not_paired'].pop(rec_id)
            revert_lists['paired'].append(self.create_revert_operation(last_change, rec, passed_since))
        else:
            if rec_id in revert_lists['not_paired']:
                if rec['action'] == ACTIONS.CREATE.value:
                    last_change = revert_lists['not_paired'].pop(rec_id)
                    revert_lists['paired'].append(self.create_revert_operation(last_change, rec, passed_since))
            elif rec['action'] == ACTIONS.CREATE.value:
                revert_lists['paired'].append(self.create_revert_operation(rec, None, passed_since))
            else:
                revert_lists['not_paired'][rec_id] = rec

    def build_revert_list(self):
        revert_lists = {'not_paired': {}, 'paired': []}
        passed_since = False
        for rec in self.history:
            if not passed_since and rec['last_modified'] < self.since:
                passed_since = True
            if passed_since and len(revert_lists['not_paired']) == 0:
                break
            self.insert_rec_to_revert_lists(rec, revert_lists, passed_since)

        return revert_lists['paired']


revert_service = Service(name="revert",
                     path='/buckets/{bucket_id}/revert',
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
    revert = Revert(request)
    return revert.revert_changes()
