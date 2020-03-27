import functools
import logging

from pyramid.security import Authenticated, IAuthorizationPolicy
from pyramid.settings import aslist
from zope.interface import implementer

from kinto.core import utils
from kinto.core.storage import exceptions as storage_exceptions

logger = logging.getLogger(__name__)

# When permission is set to "private", only the current user is allowed.
PRIVATE = "private"

# A permission is called "dynamic" when it's computed at request time.
DYNAMIC = "dynamic"


def groupfinder(userid, request):
    """Fetch principals from permission backend for the specified `userid`.

    This is plugged by default using the ``multiauth.groupfinder`` setting.
    """
    backend = getattr(request.registry, "permission", None)
    # Permission backend not configured. Ignore.
    if not backend:
        return []

    # Safety check when Kinto-Core is used without pyramid_multiauth.
    if request.prefixed_userid:
        userid = request.prefixed_userid

    # Query the permission backend only once per request (e.g. batch).
    reify_key = userid + "_principals"
    if reify_key not in request.bound_data:
        principals = backend.get_user_principals(userid)
        request.bound_data[reify_key] = principals

    return request.bound_data[reify_key]


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy:
    """Default authorization class, that leverages the permission backend
    for shareable resources.
    """

    get_bound_permissions = None
    """Callable that takes an object id and a permission and returns
    a list of tuples (<object id>, <permission>). Useful when objects
    permission depend on others."""

    def permits(self, context, principals, permission):
        if permission == PRIVATE:
            # When using the private permission, we bypass the permissions
            # backend, and simply authorize if authenticated.
            return Authenticated in principals

        principals = context.get_prefixed_principals()

        create_permission = f"{context.resource_name}:create"

        permission = context.required_permission
        if permission == "create":
            permission = create_permission

        object_id = context.permission_object_id
        bound_perms = self._get_bound_permissions(object_id, permission)

        allowed = context.check_permission(principals, bound_perms)

        # Here we consider that parent URI is one path level above.
        parent_uri = "/".join(object_id.split("/")[:-1]) if object_id else None

        # If not allowed to delete/patch, and target object is missing, and
        # allowed to read the parent, then view is permitted (will raise 404
        # later anyway). See Kinto/kinto#918
        is_object_unknown = not context.on_plural_endpoint and context.current_object is None
        if context.required_permission == "write" and is_object_unknown:
            bound_perms = self._get_bound_permissions(parent_uri, "read")
            allowed = context.check_permission(principals, bound_perms)

        # If not allowed on this plural endpoint, but some objects are shared with
        # the current user, then authorize.
        # The :class:`kinto.core.resource.Resource` class will take care of the filtering.
        is_list_operation = (
            context.on_plural_endpoint
            and not permission.endswith("create")
            and context.current_object is None
        )
        if not allowed and is_list_operation:
            allowed = bool(
                context.fetch_shared_objects(permission, principals, self.get_bound_permissions)
            )
            if not allowed:
                # If allowed to create this kind of object on parent,
                # then allow to obtain the list.
                if len(bound_perms) > 0:
                    bound_perms = [(parent_uri, create_permission)]
                else:
                    bound_perms = [("", "create")]  # Root object.
                allowed = context.check_permission(principals, bound_perms)

        if not allowed:
            logger.warning(
                "Permission %r on %r not granted to %r.",
                permission,
                object_id,
                principals[0],
                extra=dict(userid=principals[0], uri=object_id, perm=permission),
            )

        return allowed

    def _get_bound_permissions(self, object_id, permission):
        if self.get_bound_permissions is None:
            # Permission to 'write' gives permission to 'read'.
            bound = [(object_id, permission)]
            if permission == "read":
                bound += [(object_id, "write")]
            return bound
        return self.get_bound_permissions(object_id, permission)

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER


class RouteFactory:
    resource_name = None
    on_plural_endpoint = False
    required_permission = None
    permission_object_id = None
    current_object = None
    shared_ids = None

    method_permissions = {
        "head": "read",
        "get": "read",
        "post": "create",
        "delete": "write",
        "patch": "write",
    }

    def __init__(self, request):
        # Store some shortcuts.
        permission = request.registry.permission
        self._check_permission = permission.check_permission
        self._get_accessible_objects = permission.get_accessible_objects

        self.get_prefixed_principals = functools.partial(utils.prefixed_principals, request)

        # Store current resource and required permission.
        service = utils.current_service(request)
        is_on_resource = (
            service is not None and hasattr(service, "viewset") and hasattr(service, "resource")
        )
        self._resource = None
        if is_on_resource:
            self.resource_name = request.current_resource_name
            self.on_plural_endpoint = getattr(service, "type", None) == "plural"

            # Check if this request targets an individual object.
            # Its existence will affect permissions checking (cf `_find_required_permission()`).
            # There are cases where the permission is not directly related to the HTTP method,
            # For example:
            # - with POST on plural endpoint, with an id supplied
            # - with PUT on an object, which can either be creation or update
            is_write_on_object = not self.on_plural_endpoint and request.method.lower() in (
                "put",
                "delete",
                "patch",
            )
            is_post_on_plural = self.on_plural_endpoint and request.method.lower() == "post"
            if is_write_on_object or is_post_on_plural:
                # We instantiate the resource to determine the object targeted by the request.
                self._resource = resource = service.resource(request=request, context=self)
                if resource.object_id is not None:  # Skip POST on plural without id.
                    try:
                        # Save a reference, to avoid refetching from storage in resource.
                        self.current_object = resource.model.get_object(resource.object_id)
                    except storage_exceptions.ObjectNotFoundError:
                        pass

            self.permission_object_id, self.required_permission = self._find_required_permission(
                request, service
            )

            # To obtain shared objects on a plural endpoint, use a match:
            self._object_id_match = self.get_permission_object_id(request, "*")

        self._settings = request.registry.settings

    def check_permission(self, principals, bound_perms):
        """Read allowed principals from settings, if not any, query the permission
        backend to check if view is allowed.
        """
        if not bound_perms:
            bound_perms = [(self.resource_name, self.required_permission)]
        for (_, permission) in bound_perms:
            # With Kinto inheritance tree, we can have: `permission = "record:create"`
            if self.resource_name and permission.startswith(self.resource_name):
                setting = f"{permission.replace(':', '_')}_principals"
            else:
                setting = f"{self.resource_name}_{permission}_principals"
            allowed_principals = aslist(self._settings.get(setting, ""))
            if allowed_principals:
                if bool(set(allowed_principals) & set(principals)):
                    return True
        return self._check_permission(principals, bound_perms)

    def fetch_shared_objects(self, perm, principals, get_bound_permissions):
        """Fetch objects that are readable or writable for the current
        principals.

        See :meth:`kinto.core.authorization.AuthorizationPolicy.permits`

        If no object is shared, it returns None.

        .. warning::
            This sets the ``shared_ids`` attribute to the context with the
            return value. The attribute is then read by
            :class:`kinto.core.resource.Resource`
        """
        if get_bound_permissions:
            bound_perms = get_bound_permissions(self._object_id_match, perm)
        else:
            bound_perms = [(self._object_id_match, perm)]
        by_obj_id = self._get_accessible_objects(principals, bound_perms, with_children=False)
        ids = by_obj_id.keys()
        # Store for later use in ``Resource``.
        self.shared_ids = [self._extract_object_id(id_) for id_ in ids]
        return self.shared_ids

    def get_permission_object_id(self, request, object_id=None):
        """Returns the permission object id for the current request.
        In the nominal case, it is just the current URI without version prefix.
        For plural endpoint, it is the related object URI using the specified
        `object_id`.

        See :meth:`kinto.core.resource.model.SharableModel` and
        :meth:`kinto.core.authorization.RouteFactory.__init__`
        """
        object_uri = utils.strip_uri_prefix(request.path)

        if self.on_plural_endpoint and object_id is not None:
            # With the current request on a plural endpoint, the object URI must
            # be found out by inspecting the "plural" service and its sibling
            # "object" service. (see `register_resource()`)
            matchdict = {**request.matchdict, "id": object_id}
            try:
                object_uri = utils.instance_uri(request, self.resource_name, **matchdict)
                object_uri = object_uri.replace("%2A", "*")
            except KeyError:
                # Maybe the resource has no single object endpoint.
                # We consider that object URIs in permissions backend will
                # be stored naively:
                object_uri = f"{object_uri}/{object_id}"

        return object_uri

    def _extract_object_id(self, object_uri):
        # XXX: Rewrite using kinto.core.utils.view_lookup() and matchdict['id']
        return object_uri.split("/")[-1]

    def _find_required_permission(self, request, service):
        """Find out what is the permission object id and the required
        permission.

        .. note::
            This method saves an attribute ``self.current_object`` used
            in :class:`kinto.core.resource.Resource`.
        """
        # By default, it's a URI a and permission associated to the method.
        permission_object_id = self.get_permission_object_id(request)
        method = request.method.lower()
        required_permission = self.method_permissions.get(method)

        # For create permission, the object id is the plural endpoint.
        plural_path = str(service.plural_path)
        plural_path = plural_path.format_map(request.matchdict)

        # In the case of a "PUT", check if the targetted object already
        # exists, return "write" if it does, "create" otherwise.
        if request.method.lower() == "put":
            if self.current_object is None:
                # The object does not exist, the permission to create on
                # the related plural endpoint is required.
                permission_object_id = plural_path
                required_permission = "create"
            else:
                # For safe creations, the user needs a create permission.
                # See Kinto/kinto#792
                if request.headers.get("If-None-Match") == "*":
                    permission_object_id = plural_path
                    required_permission = "create"
                else:
                    required_permission = "write"

        # In the case of a "POST" on a plural endpoint, if an "id" was
        # specified, then the object is returned. The required permission
        # is thus "read" on this object.
        if request.method.lower() == "post" and self.current_object is not None:
            permission_object_id = self.get_permission_object_id(
                request, object_id=self._resource.object_id
            )
            required_permission = "read"

        return (permission_object_id, required_permission)
