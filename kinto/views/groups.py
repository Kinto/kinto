import colander
from pyramid.events import subscriber

from kinto.core import resource, utils
from kinto.core.events import ResourceChanged, ACTIONS
from kinto.schema_validation import validate_from_bucket_schema_or_400


def validate_member(node, member):
    if member.startswith("/buckets/") or member == "system.Everyone":
        raise colander.Invalid(node, f"'{member}' is not a valid user ID.")


class GroupSchema(resource.ResourceSchema):
    members = colander.SchemaNode(
        colander.Sequence(),
        colander.SchemaNode(colander.String(), validator=validate_member),
        missing=[],
    )


@resource.register(
    name="group",
    plural_path="/buckets/{{bucket_id}}/groups",
    object_path="/buckets/{{bucket_id}}/groups/{{id}}",
)
class Group(resource.Resource):
    schema = GroupSchema

    def get_parent_id(self, request):
        bucket_id = request.matchdict["bucket_id"]
        parent_id = utils.instance_uri(request, "bucket", id=bucket_id)
        return parent_id

    def process_object(self, new, old=None):
        """Additional collection schema validation from bucket, if any."""
        new = super().process_object(new, old)

        # Remove internal and auto-assigned fields.
        internal_fields = (self.model.modified_field, self.model.permissions_field)
        validate_from_bucket_schema_or_400(
            new,
            resource_name="group",
            request=self.request,
            ignore_fields=internal_fields,
            id_field=self.model.id_field,
        )

        return new


@subscriber(ResourceChanged, for_resources=("group",), for_actions=(ACTIONS.DELETE,))
def on_groups_deleted(event):
    """Some groups were deleted, remove them from users principals.
    """
    permission_backend = event.request.registry.permission

    for change in event.impacted_objects:
        group = change["old"]
        bucket_id = event.payload["bucket_id"]
        group_uri = utils.instance_uri(event.request, "group", bucket_id=bucket_id, id=group["id"])

        permission_backend.remove_principal(group_uri)


@subscriber(
    ResourceChanged, for_resources=("group",), for_actions=(ACTIONS.CREATE, ACTIONS.UPDATE)
)
def on_groups_changed(event):
    """Some groups were changed, update users principals.
    """
    permission_backend = event.request.registry.permission

    for change in event.impacted_objects:
        if "old" in change:
            existing_record_members = set(change["old"].get("members", []))
        else:
            existing_record_members = set()

        group = change["new"]
        group_uri = f"/buckets/{event.payload['bucket_id']}/groups/{group['id']}"
        new_record_members = set(group.get("members", []))
        new_members = new_record_members - existing_record_members
        removed_members = existing_record_members - new_record_members

        for member in new_members:
            # Add the group to the member principal.
            permission_backend.add_user_principal(member, group_uri)

        for member in removed_members:
            # Remove the group from the member principal.
            permission_backend.remove_user_principal(member, group_uri)
