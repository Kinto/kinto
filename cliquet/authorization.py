from pyramid.security import Allow, IAuthorizationPolicy

from cliquet import utils
from cliquet.storage import exceptions as storage_exceptions


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        if permission is None:
            permission = context.required_permission
        object_id = context.object_id
        get_bound_permissions = context.get_bound_permissions
        has_permission = context.permission.has_permission

        if permission == 'create':
            permission = '%s:%s' % (context.object_type, permission)

        return has_permission(object_id, permission, principals,
                              get_bound_permissions)

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER


class RouteFactory(object):
    # Callable which return a set of bound permissions for the given
    # object id and unbound permission.
    get_bound_permissions = None
    method_permissions = {
        "head": "read",
        "get": "read",
        "post": "create",
        "delete": "write",
        "patch": "write"
    }

    def __init__(self, request):
        # Decide what the required unbound permission is depending on the
        # method that's being requested.
        if request.method.lower() == "put":
            # In the case of a "PUT", check if the associated record already
            # exists, return "write" if it does, "create" otherwise.
            # For now, consider whoever puts should have "create" access.
            service = utils.current_service(request)

            # If the view exists, call it with the request and catch an
            # eventual NotFound.
            if service is not None:
                resource = service.resource(request)
                try:
                    resource.collection.get_record(resource.record_id)
                except storage_exceptions.RecordNotFoundError:
                    permission = "create"
                else:
                    permission = "write"
        else:
            permission = self.method_permissions[request.method.lower()]
        self.required_permission = permission
