from pyramid.security import Allow


class RouteFactory(object):
    get_bound_permissions = None
    method_permissions = {
        "head": "read",
        "get": "read",
        "post": "create",
        "delete": "write",
        "patch": "write"
    }

    def __init__(self, request):
        # Define some aliases for a longer life.
        perm_backend = request.registry.permission
        get_principals = perm_backend.object_permission_authorized_principals

        # Decide what the required unbound permission is depending on the
        # method that's being requested.
        if request.method.lower() == "put":
            # In the case of a "PUT", check if the associated record already
            # exists, return "write" if it does, "create" otherwise.
            # For now, consider whoever puts should have "create" access.
            permission = "create"
        else:
            permission = self.method_permissions[request.method.lower()]

        acls = get_principals(request.upath_info, permission,
                              self.get_bound_permissions)
        self.__acl__ = [(Allow, principal, perm) for principal, perm in acls]
