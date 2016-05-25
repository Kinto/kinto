from cornice import Service
from pyramid.request import Request
from pyramid.interfaces import IRoutesMapper
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE


permissions = Service(name='permissions',
                      description='List of user permissions',
                      path='/permissions')


@permissions.get(permission=NO_PERMISSION_REQUIRED)
def permissions_get(request):
    backend = request.registry.permission
    # XXX : add setting experimental?
    # XXX : if backend is None, route should be ignored in kinto init

    possible_perms = set([k.split(':', 1)[1]
                          for k in PERMISSIONS_INHERITANCE_TREE.keys()])

    perms_descending_tree = {}
    for obtained_perm, obtained_from in PERMISSIONS_INHERITANCE_TREE.items():
        for resource, perms in obtained_from.items():
            for perm in perms:
                perms_descending_tree.setdefault(resource, {})\
                                     .setdefault(perm, set())\
                                     .add(obtained_perm)

    # Obtain current principals.
    principals = request.effective_principals
    if Authenticated in principals:
        # XXX: since view does not require permission, had to do this:
        userid = request.prefixed_userid
        principals.append(userid)

    perms_by_object_uri = {}
    for perm in possible_perms:
        object_uris = backend.principals_accessible_objects(principals, perm)
        for object_uri in object_uris:
            perms_by_object_uri.setdefault(object_uri, []).append(perm)

    api_prefix = '/%s' % request.upath_info.split('/')[1]
    q = request.registry.queryUtility
    routes_mapper = q(IRoutesMapper)

    entries = []
    for object_uri, perms in perms_by_object_uri.items():
        # Obtain associated resource to object URI
        # XXX: move to core.utils
        fakerequest = Request.blank(path=api_prefix + object_uri)
        info = routes_mapper(fakerequest)
        match, route = info['match'], info['route']
        resource_name = route.name.replace('-record', '')\
                                  .replace('-collection', '')
        match['%s_id' % resource_name] = match.pop('id')

        permissions = set(perms)
        for perm in perms:
            obtained = perms_descending_tree[resource_name][perm]
            shown = [p.split(':', 1)[1]
                     for p in obtained if p.startswith(resource_name)]
            permissions |= set(shown)

        entry = dict(uri=object_uri,
                     resource_name=resource_name,
                     permissions=list(permissions),
                     **match)
        entries.append(entry)

    return {"data": entries}
