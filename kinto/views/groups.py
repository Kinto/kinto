import colander

from kinto.core import resource, utils
from kinto.core.errors import http_error, ERRORS
from kinto.core.events import ResourceChanged, ACTIONS
from pyramid.events import subscriber
from pyramid.httpexceptions import HTTPBadRequest


class GroupSchema(resource.ResourceSchema):
    members = colander.SchemaNode(colander.Sequence(),
                                  colander.SchemaNode(colander.String()))


@resource.register(name='group',
                   collection_path='/buckets/{{bucket_id}}/groups',
                   record_path='/buckets/{{bucket_id}}/groups/{{id}}')
class Group(resource.ShareableResource):
    mapping = GroupSchema()

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        parent_id = utils.instance_uri(request, 'bucket', id=bucket_id)
        return parent_id

    def process_record(self, *args, **kwargs):
        record = super(Group, self).process_record(*args, **kwargs)
        for member in record['members']:
            if member.startswith('/buckets/') or member == 'system.Everyone':
                raise http_error(HTTPBadRequest(),
                                 errno=ERRORS.INVALID_PARAMETERS,
                                 message="'%s' is not a valid user ID." % member)
        return record


@subscriber(ResourceChanged,
            for_resources=('group',),
            for_actions=(ACTIONS.DELETE,))
def on_groups_deleted(event):
    """Some groups were deleted, remove them from users principals.
    """
    permission_backend = event.request.registry.permission

    for change in event.impacted_records:
        group = change['old']
        bucket_id = event.payload['bucket_id']
        group_uri = utils.instance_uri(event.request, 'group',
                                       bucket_id=bucket_id,
                                       id=group['id'])

        permission_backend.remove_principal(group_uri)


@subscriber(ResourceChanged,
            for_resources=('group',),
            for_actions=(ACTIONS.CREATE, ACTIONS.UPDATE))
def on_groups_changed(event):
    """Some groups were changed, update users principals.
    """
    permission_backend = event.request.registry.permission

    for change in event.impacted_records:
        if 'old' in change:
            existing_record_members = set(change['old'].get('members', []))
        else:
            existing_record_members = set()

        group = change['new']
        group_uri = '/buckets/{bucket_id}/groups/{id}'.format(id=group['id'],
                                                              **event.payload)
        new_record_members = set(group.get('members', []))
        new_members = new_record_members - existing_record_members
        removed_members = existing_record_members - new_record_members

        for member in new_members:
            # Add the group to the member principal.
            permission_backend.add_user_principal(member, group_uri)

        for member in removed_members:
            # Remove the group from the member principal.
            permission_backend.remove_user_principal(member, group_uri)
