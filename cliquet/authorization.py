import re
import six
from pyramid.security import IAuthorizationPolicy
from zope.interface import implementer

from cliquet import utils
from cliquet.storage import exceptions as storage_exceptions


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        if permission == 'dynamic':
            permission = context.required_permission
        object_id = context.object_id
        get_bound_permissions = context.get_bound_permissions
        has_permission = context.has_permission

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
        service = utils.current_service(request)
        object_id = get_object_id(request)
        self.object_type = service.viewset.get_name(service.resource)
        # Decide what the required unbound permission is depending on the
        # method that's being requested.
        if request.method.lower() == "put":
            # In the case of a "PUT", check if the associated record already
            # exists, return "write" if it does, "create" otherwise.
            # For now, consider whoever puts should have "create" access.

            # If the view exists, call it with the request and catch an
            # eventual NotFound.
            if service is not None:
                resource = service.resource(request)
                try:
                    resource.collection.get_record(resource.record_id)
                except storage_exceptions.RecordNotFoundError:
                    object_id = service.collection_path
                    permission = "create"
                else:
                    permission = "write"
        else:
            permission = self.method_permissions[request.method.lower()]

        self.required_permission = permission
        self.object_id = object_id
        self.has_permission = request.registry.permission.has_permission


def get_object_id(request):
    record_uri = request.path

    # Remove potential version prefix in URI.
    return re.sub(r'^(/v\d+)?', '', six.text_type(record_uri))
