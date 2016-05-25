from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.core import utils as core_utils


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
        # XXX: since view does not require permission, had to do this:
        userid = request.prefixed_userid
        principals.append(userid)

    # Query every possible permission from backend.
    # XXX: this is a workaround because there is no "full-list" method.
    possible_perms = set([k.split(':', 1)[1]
                          for k in PERMISSIONS_INHERITANCE_TREE.keys()])
    backend = request.registry.permission
    perms_by_object_uri = {}
    for perm in possible_perms:
        object_uris = backend.principals_accessible_objects(principals, perm)
        for object_uri in object_uris:
            perms_by_object_uri.setdefault(object_uri, []).append(perm)

    entries = []
    for object_uri, perms in perms_by_object_uri.items():
        # Obtain associated resource from object URI
        resource_name, matchdict = core_utils.view_lookup(request, object_uri)
        # XXX: do we want bucket_id, record_id or just id ?
        matchdict['%s_id' % resource_name] = matchdict.pop('id')

        # Expand implicit permissions using descending tree.
        permissions = set(perms)
        for perm in perms:
            obtained = perms_descending_tree[resource_name][perm]
            # Related to same resource only (not every sub-objects).
            permissions |= obtained[resource_name]

        entry = dict(uri=object_uri,
                     resource_name=resource_name,
                     permissions=list(permissions),
                     **matchdict)
        entries.append(entry)

    return {"data": entries}
