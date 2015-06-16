import colander

from cliquet import resource
from cliquet import schema

from cliquet.authorization import get_object_id

from kinto.views import NameGenerator, object_exists_or_404


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

        bucket_id = self.request.matchdict['bucket_id']
        object_exists_or_404(self.request,
                             collection_id='bucket',
                             object_id=bucket_id)

        parent_id = '/buckets/%s' % bucket_id
        self.collection.parent_id = parent_id
        self.collection.id_generator = NameGenerator()

    def collection_delete(self):
        filters = self._extract_filters()
        groups, _ = self.collection.get_records(filters=filters)
        body = super(Group, self).collection_delete()
        permission = self.request.registry.permission
        for group in groups:
            # Remove the group's principal from all members of the group.
            for member in group['members']:
                group_id = '%s/%s' % (get_object_id(self.request.path),
                                      group['id'])
                permission.remove_user_principal(
                    member,
                    group_id)
        return body

    def delete(self):
        group = self._get_record_or_404(self.record_id)
        permission = self.request.registry.permission
        body = super(Group, self).delete()
        object_id = get_object_id(self.request.path)
        for member in group['members']:
            # Remove the group's principal from all members of the group.
            permission.remove_user_principal(member, object_id)
        return body

    def process_record(self, new, old=None):
        if old is None:
            existing_record_members = set([])
        else:
            existing_record_members = set(old['members'])
        new_record_members = set(new['members'])
        new_members = new_record_members - existing_record_members
        removed_members = existing_record_members - new_record_members

        permission = self.request.registry.permission
        for member in new_members:
            # Add the group to the member principal.
            group_id = get_object_id(self.request.path)
            permission.add_user_principal(member, group_id)

        for member in removed_members:
            # Remove the group from the member principal.
            group_id = get_object_id(self.request.path)
            permission.remove_user_principal(member, group_id)

        return new
