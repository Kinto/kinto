import re

import colander
from pyramid.settings import aslist

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core import resource
from kinto.core import utils as core_utils
from kinto.core.storage import Sort
from kinto.core.storage.memory import extract_object_set


def allowed_from_settings(settings, principals):
    """Returns every permissions allowed from settings for the current user.
    :param settings dict: app settings
    :param principals list: list of principals of current user
    :rtype: dict

    Result example::

        {
            "bucket": {"write", "collection:create"},
            "collection": {"read"}
        }

    XXX: This helper will be useful for Kinto/kinto#894
    """
    # Select settings about explicit permissions set on resources
    # bucket_write_principals = ... --> {("bucket", "write"): ["account:admin"]}
    perms_settings = {
        tuple(k.split("_", 3)[:2]): aslist(v)
        for k, v in settings.items()
        if re.match("(.+)_(create|write|read)_principals", k)
    }

    from_settings = {}
    for (resource_name, permission), allowed_principals in perms_settings.items():
        # Keep the known permissions only.
        if resource_name not in PERMISSIONS_INHERITANCE_TREE.keys():
            continue
        # Keep the permissions of the current user only.
        if not bool(set(principals) & set(allowed_principals)):
            continue
        # ``collection_create_principals`` means ``collection:create`` in bucket.
        if permission == "create":
            permission = f"{resource_name}:{permission}"
            resource_name = {  # resource parents.
                "collection": "bucket",
                "group": "bucket",
                "record": "collection",
                "bucket": "root",
                "account": "root",
            }.get(resource_name, "")
        # Store them in a convenient way.
        from_settings.setdefault(resource_name, set()).add(permission)
    return from_settings


class PermissionsModel:
    id_field = "id"
    modified_field = "last_modified"
    deleted_field = "deleted"

    def __init__(self, request):
        self.request = request

    def timestamp(self, parent_id=None):
        return 0

    def get_objects(
        self,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        parent_id=None,
    ):
        objects, _ = self._get_objects(
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            include_deleted=include_deleted,
            parent_id=parent_id,
        )
        return objects

    def count_objects(self, filters=None, parent_id=None):
        _, count = self._get_objects(filters=filters, parent_id=parent_id)
        return count

    def _get_objects(
        self,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        parent_id=None,
    ):
        # Invert the permissions inheritance tree.
        perms_descending_tree = {}
        for on_resource, tree in PERMISSIONS_INHERITANCE_TREE.items():
            for obtained_perm, obtained_from in tree.items():
                for from_resource, perms in obtained_from.items():
                    for perm in perms:
                        perms_descending_tree.setdefault(from_resource, {}).setdefault(
                            perm, {}
                        ).setdefault(on_resource, set()).add(obtained_perm)

        # Obtain current principals.
        principals = self.request.prefixed_principals

        # Query every possible permission of the current user from backend.
        backend = self.request.registry.permission
        perms_by_object_uri = backend.get_accessible_objects(principals)

        # Check settings for every allowed resources.
        from_settings = allowed_from_settings(self.request.registry.settings, principals)

        # Add additional resources and permissions defined in settings/plugins
        for root_perm in from_settings.get("root", []):
            resource_name, _ = root_perm.split(":")
            perms_by_object_uri.setdefault("/", set()).add(root_perm)
            perms_descending_tree.setdefault("root", {}).update({root_perm: {"root": {root_perm}}})

        # Expand permissions obtained from backend with the object URIs that
        # correspond to permissions allowed from settings.
        allowed_resources = {"bucket", "collection", "group"} & set(from_settings.keys())
        if allowed_resources:
            storage = self.request.registry.storage
            every_bucket = storage.list_all(parent_id="", resource_name="bucket")
            for bucket in every_bucket:
                bucket_uri = "/buckets/{id}".format_map(bucket)
                for res in allowed_resources:
                    resource_perms = from_settings[res]
                    # Bucket is always fetched.
                    if res == "bucket":
                        perms_by_object_uri.setdefault(bucket_uri, set()).update(resource_perms)
                        continue
                    # Fetch bucket collections and groups.
                    # XXX: wrong approach: query in a loop!
                    every_subobjects = storage.list_all(parent_id=bucket_uri, resource_name=res)
                    for subobject in every_subobjects:
                        subobj_uri = bucket_uri + f"/{res}s/{subobject['id']}"
                        perms_by_object_uri.setdefault(subobj_uri, set()).update(resource_perms)

        entries = []
        for object_uri, perms in perms_by_object_uri.items():
            try:
                # Obtain associated res from object URI
                resource_name, matchdict = core_utils.view_lookup(self.request, object_uri)
            except ValueError:
                # Skip permissions entries that are not linked to an object URI
                continue

            # For consistency with event payloads, if resource has an id,
            # prefix it with its resource name
            if "id" in matchdict:
                matchdict[resource_name + "_id"] = matchdict["id"]

            # The imaginary "root" resource gets mapped to the hello
            # view. Handle it explicitly.
            if resource_name == "hello":
                resource_name = "root"

            # Expand implicit permissions using descending tree.
            permissions = set(perms)
            for perm in perms:
                obtained = perms_descending_tree[resource_name][perm]
                # Related to same resource only and not every sub-objects.
                # (e.g "bucket:write" gives "bucket:read" but not "group:read")
                permissions |= obtained[resource_name]

            entry = dict(
                uri=object_uri,
                resource_name=resource_name,
                permissions=list(permissions),
                **matchdict,
            )
            entries.append(entry)

        return extract_object_set(
            entries,
            filters=filters,
            sorting=sorting,
            id_field="uri",
            pagination_rules=pagination_rules,
            limit=limit,
        )


class PermissionsSchema(resource.ResourceSchema):
    uri = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    permissions = colander.Sequence(colander.SchemaNode(colander.String()))
    bucket_id = colander.SchemaNode(colander.String())
    collection_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    group_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    record_id = colander.SchemaNode(colander.String(), missing=colander.drop)

    class Options:
        preserve_unknown = False


@resource.register(
    name="permissions",
    description="List of user permissions",
    plural_path="/permissions",
    object_path=None,
    plural_methods=("HEAD", "GET"),
)
class Permissions(resource.Resource):

    schema = PermissionsSchema

    def __init__(self, request, context=None):
        super().__init__(request, context)
        self.model = PermissionsModel(request)

    def _extract_sorting(self, limit):
        # Permissions entries are not stored with timestamp, so do not
        # force it.
        result = super()._extract_sorting(limit)
        without_last_modified = [s for s in result if s.field != self.model.modified_field]
        # For pagination, there must be at least one sort criteria.
        # We use ``uri`` because its values are unique.
        if "uri" not in [s.field for s in without_last_modified]:
            without_last_modified.append(Sort("uri", -1))
        return without_last_modified

    def _extract_filters(self):
        result = super()._extract_filters()
        without_last_modified = [s for s in result if s.field != self.model.modified_field]
        return without_last_modified
