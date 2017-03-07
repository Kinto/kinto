import colander

from kinto.core import resource, utils
from kinto.core.events import ResourceChanged, ACTIONS
from pyramid.events import subscriber


def validate_member(node, member):
    if member.startswith('/buckets/') or member == 'system.Everyone':
        raise colander.Invalid(node, "'{}' is not a valid user ID.".format(member))


class GroupSchema(resource.ResourceSchema):
    members = colander.SchemaNode(colander.Sequence(),
                                  colander.SchemaNode(colander.String(),
                                                      validator=validate_member),
                                  missing=[])


@resource.register(name='group',
                   collection_path='/buckets/{{bucket_id}}/groups',
                   record_path='/buckets/{{bucket_id}}/groups/{{id}}')
class Group(resource.ShareableResource):
    schema = GroupSchema

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        parent_id = utils.instance_uri(request, 'bucket', id=bucket_id)
        return parent_id


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
