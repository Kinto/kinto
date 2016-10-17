import colander
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core import utils as core_utils, resource
from kinto.core.storage.memory import extract_record_set


class PermissionsModel(object):
    id_field = 'id'
    modified_field = 'last_modified'
    deleted_field = 'deleted'

    def __init__(self, request):
        self.request = request

    def get_records(self, filters=None, sorting=None, pagination_rules=None,
                    limit=None, include_deleted=False, parent_id=None):
        # Invert the permissions inheritance tree.
        perms_descending_tree = {}
        for on_resource, tree in PERMISSIONS_INHERITANCE_TREE.items():
            for obtained_perm, obtained_from in tree.items():
                for from_resource, perms in obtained_from.items():
                    for perm in perms:
                        perms_descending_tree.setdefault(from_resource, {})\
                                             .setdefault(perm, {})\
                                             .setdefault(on_resource, set())\
                                             .add(obtained_perm)

        # Obtain current principals.
        principals = self.request.effective_principals
        if Authenticated in principals:
            # Since this view does not require any permission (can be used to
            # obtain public users permissions), we have to add the prefixed
            # userid among the principals
            # (see :mod:`kinto.core.authentication`)
            userid = self.request.prefixed_userid
            principals.append(userid)

        # Query every possible permission of the current user from backend.
        backend = self.request.registry.permission
        perms_by_object_uri = backend.get_accessible_objects(principals)

        entries = []
        for object_uri, perms in perms_by_object_uri.items():
            try:
                # Obtain associated resource from object URI
                resource_name, matchdict = core_utils.view_lookup(self.request,
                                                                  object_uri)
            except ValueError:
                # Skip permissions entries that are not linked to an object URI
                continue

            # For consistency with event payloads, prefix id with resource name
            matchdict[resource_name + '_id'] = matchdict.get('id')

            # Expand implicit permissions using descending tree.
            permissions = set(perms)
            for perm in perms:
                obtained = perms_descending_tree[resource_name][perm]
                # Related to same resource only and not every sub-objects.
                # (e.g "bucket:write" gives "bucket:read" but not "group:read")
                permissions |= obtained[resource_name]

            entry = dict(uri=object_uri,
                         resource_name=resource_name,
                         permissions=list(permissions),
                         **matchdict)
            entries.append(entry)

        return extract_record_set(entries, filters=filters, sorting=sorting,
                                  pagination_rules=pagination_rules,
                                  limit=limit)


class PermissionsSchema(resource.ResourceSchema):
    uri = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    permissions = colander.Sequence(colander.SchemaNode(colander.String()))
    bucket_id = colander.SchemaNode(colander.String())
    collection_id = colander.SchemaNode(colander.String(),
                                        missing=colander.drop)
    group_id = colander.SchemaNode(colander.String(),
                                   missing=colander.drop)
    record_id = colander.SchemaNode(colander.String(),
                                    missing=colander.drop)

    class Options:
        preserve_unknown = False


@resource.register(name='permissions',
                   description='List of user permissions',
                   collection_path='/permissions',
                   record_path=None,
                   collection_methods=('GET',),
                   permission=NO_PERMISSION_REQUIRED)
class Permissions(resource.ShareableResource):

    mapping = PermissionsSchema()

    def __init__(self, request, context=None):
        super(Permissions, self).__init__(request, context)
        self.model = PermissionsModel(request)

    def _extract_sorting(self, limit):
        # Permissions entries are not stored with timestamp, so do not
        # force it.
        result = super(Permissions, self)._extract_sorting(limit)
        without_last_modified = [s for s in result
                                 if s.field != self.model.modified_field]
        return without_last_modified

    def _extract_filters(self, queryparams=None):
        result = super(Permissions, self)._extract_filters(queryparams)
        without_last_modified = [s for s in result
                                 if s.field != self.model.modified_field]
        return without_last_modified
