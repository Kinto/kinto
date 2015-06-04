METHOD_PERMISSIONS = {
    "head": "read",
    "get": "read",
    "post": "create",
    "put": "write",  # or create, depending if something exists or not.
    "delete": "write",  # write or create?
}


class RouteFactory(object):
    get_bound_permissions = None

    def __init__(self, request):
        # Define some aliases for a longer life.
        perm_backend = request.registry.permission
        get_principals = perm_backend.object_permission_authorized_principals

        # Decide what the required unbound permission is depending on the
        # method that's being requested.
        permission = METHOD_PERMISSIONS[request.method.lower()]
        acls = get_principals(request.upath_info, permission,
                              self.get_bound_permissions)
        self.__acl__ = [(Allow, principal, perm) for principal, perm in acls]
