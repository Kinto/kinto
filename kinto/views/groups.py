import colander

from cliquet import resource
from cliquet.events import ResourceChanged, ACTIONS
from pyramid.events import subscriber

from kinto.views import NameGenerator


class GroupSchema(resource.ResourceSchema):
    members = colander.SchemaNode(colander.Sequence(),
                                  colander.SchemaNode(colander.String()))

    class Options:
        preserve_unknown = True


@resource.register(name='group',
                   collection_path='/buckets/{{bucket_id}}/groups',
                   record_path='/buckets/{{bucket_id}}/groups/{{id}}')
class Group(resource.ShareableResource):

    mapping = GroupSchema()

    def __init__(self, *args, **kwargs):
        super(Group, self).__init__(*args, **kwargs)
        self.model.id_generator = NameGenerator()

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        parent_id = '/buckets/%s' % bucket_id
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
        group_uri = '/buckets/{bucket_id}/groups/{id}'.format(id=group['id'],
                                                              **event.payload)
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
