import colander

from cliquet import resource
from cliquet import schema

from kinto.views import NameGenerator


class GroupSchema(schema.ResourceSchema):
    members = colander.SchemaNode(colander.Sequence(),
                                  colander.SchemaNode(colander.String()))


@resource.register(name='group',
                   collection_path='/buckets/{{bucket_id}}/groups',
                   record_path='/buckets/{{bucket_id}}/groups/{{id}}')
class Group(resource.ProtectedResource):

    mapping = GroupSchema()

    def __init__(self, *args, **kwargs):
        super(Group, self).__init__(*args, **kwargs)
        self.model.id_generator = NameGenerator()

    def get_parent_id(self, request):
        bucket_id = request.matchdict['bucket_id']
        parent_id = '/buckets/%s' % bucket_id
        return parent_id

    def collection_delete(self):
        filters = self._extract_filters()
        groups, _ = self.model.get_records(filters=filters)
        body = super(Group, self).collection_delete()
        permission = self.request.registry.permission
        for group in groups:
            group_id = self.context.get_permission_object_id(
                self.request, group[self.model.id_field])
            # Remove the group's principal from all members of the group.
            for member in group['members']:
                permission.remove_user_principal(
                    member,
                    group_id)
        return body

    def delete(self):
        group = self._get_record_or_404(self.record_id)
        permission = self.request.registry.permission
        body = super(Group, self).delete()
        group_id = self.context.permission_object_id
        for member in group['members']:
            # Remove the group's principal from all members of the group.
            permission.remove_user_principal(member, group_id)
        return body

    def process_record(self, new, old=None):
        if old is None:
            existing_record_members = set()
        else:
            existing_record_members = set(old.get('members', []))
        new_record_members = set(new['members'])
        new_members = new_record_members - existing_record_members
        removed_members = existing_record_members - new_record_members

        group_principal = self.context.get_permission_object_id(
            self.request, self.record_id)
        permission = self.request.registry.permission
        for member in new_members:
            # Add the group to the member principal.
            permission.add_user_principal(member, group_principal)

        for member in removed_members:
            # Remove the group from the member principal.
            permission.remove_user_principal(member, group_principal)

        return new
