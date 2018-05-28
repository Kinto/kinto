import colander
from pyramid.events import subscriber
from pyramid.settings import asbool

from kinto.core import resource, utils
from kinto.core.errors import raise_invalid
from kinto.views import object_exists_or_404
from kinto.core.events import ResourceChanged, ACTIONS
from kinto.schema_validation import validate_schema, ValidationError


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        buckets = self.request.bound_data.setdefault('buckets', {})
        bucket_uri = utils.instance_uri(self.request, 'bucket', id=self.bucket_id)
        if bucket_uri not in buckets:
            bucket = object_exists_or_404(self.request,
                                          collection_id='bucket',
                                          parent_id='',
                                          object_id=self.bucket_id)
            buckets[bucket_uri] = bucket
        self._bucket = buckets[bucket_uri]

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict['bucket_id']
        parent_id = utils.instance_uri(request, 'bucket', id=self.bucket_id)
        return parent_id

    def process_record(self, new, old=None):
        """Additional group schema validation from bucket, if any."""
        new = super().process_record(new, old)

        settings = self.request.registry.settings
        schema_validation = 'experimental_collection_schema_validation'
        if not asbool(settings.get(schema_validation)) or 'group:schema' not in self._bucket:
            return new

        schema = self._bucket['group:schema']

        # Remove internal and auto-assigned fields.
        internal_fields = (self.model.id_field,
                           self.model.modified_field,
                           self.model.permissions_field)
        data = {f: v for f, v in new.items() if f not in internal_fields}

        # Validate or fail with 400.
        try:
            validate_schema(data, schema, ignore_fields=internal_fields)
        except ValidationError as e:
            raise_invalid(self.request, name=e.field, description=e.message)

        return new


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
