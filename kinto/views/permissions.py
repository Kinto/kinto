from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core import Service, utils as core_utils


permissions = Service(name='permissions',
                      description='List of user permissions',
                      path='/permissions')


@permissions.get(permission=NO_PERMISSION_REQUIRED)
def permissions_get(request):
    # Invert the permissions inheritance tree.
    perms_descending_tree = {}
    for obtained, obtained_from in PERMISSIONS_INHERITANCE_TREE.items():
        on_resource, obtained_perm = obtained.split(':', 1)
        for from_resource, perms in obtained_from.items():
            for perm in perms:
                perms_descending_tree.setdefault(from_resource, {})\
                                     .setdefault(perm, {})\
                                     .setdefault(on_resource, set())\
                                     .add(obtained_perm)

    # Obtain current principals.
    principals = request.effective_principals
    if Authenticated in principals:
        # Since this view does not require any permission (can be used to
        # obtain public users permissions), we have to add the prefixed userid
        # among the principals (see :mode:`kinto.core.authentication`)
        userid = request.prefixed_userid
        principals.append(userid)

    # Query every possible permission of the current user from backend.
    backend = request.registry.permission
    perms_by_object_uri = backend.get_accessible_objects(principals)

    entries = []
    for object_uri, perms in perms_by_object_uri.items():
        # Obtain associated resource from object URI
        resource_name, matchdict = core_utils.view_lookup(request, object_uri)
        # For consistency with events payloads, prefix id with resource name
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

    return {"data": entries}
