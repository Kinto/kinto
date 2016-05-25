from cornice import Service
from pyramid.request import Request
from pyramid.interfaces import IRoutesMapper
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated


permissions = Service(name='permissions',
                      description='List of user permissions',
                      path='/permissions')


@permissions.get(permission=NO_PERMISSION_REQUIRED)
def permissions_get(request):
    backend = request.registry.permission
    # XXX : add setting «experimental» ?
    # XXX : if backend is None, route should be ignored in kinto init

    # Obtain current principals.
    principals = request.effective_principals
    if Authenticated in principals:
        # XXX: since view does not require permission, had to do this:
        userid = request.prefixed_userid
        principals.append(userid)

    # XXX should work with read and others
    object_uris = backend.principals_accessible_objects(principals, 'write')

    q = request.registry.queryUtility
    routes_mapper = q(IRoutesMapper)

    entries = []
    for object_uri in object_uris:
        # Obtain associated resource to object URI
        # XXX: move to core.utils
        # XXX: hard coded v1
        fakerequest = Request.blank(path='/v1' + object_uri)
        info = routes_mapper(fakerequest)
        match, route = info['match'], info['route']
        resource_name = route.name.replace('-record', '')
        match['%s_id' % resource_name] = match.pop('id')

        # XXX hard coded perms tree
        # XXX: move to helper in authorization
        permissions = ['read', 'write']
        if resource_name == 'bucket':
            permissions.append('collection:create')
        elif resource_name == 'collection':
            permissions.append('record:create')

        entry = dict(uri=object_uri,
                     resource_name=resource_name,
                     permissions=permissions,
                     **match)
        entries.append(entry)

    return {"data": entries}
