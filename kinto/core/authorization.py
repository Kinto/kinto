import functools

from pyramid.settings import aslist
from pyramid.security import IAuthorizationPolicy, Authenticated
from zope.interface import implementer

from kinto.core import utils
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.authentication import prefixed_userid

# A permission is called "dynamic" when it's computed at request time.
DYNAMIC = 'dynamic'

# When permission is set to "private", only the current user is allowed.
PRIVATE = 'private'


def groupfinder(userid, request):
    """Fetch principals from permission backend for the specified `userid`.

    This is plugged by default using the ``multiauth.groupfinder`` setting.
    """
    backend = getattr(request.registry, 'permission', None)
    # Permission backend not configured. Ignore.
    if not backend:
        return []

    # Safety check when Kinto-Core is used without pyramid_multiauth.
    if request.prefixed_userid:
        userid = request.prefixed_userid

    # Query the permission backend only once per request (e.g. batch).
    reify_key = userid + '_principals'
    if reify_key not in request.bound_data:
        principals = backend.user_principals(userid)
        request.bound_data[reify_key] = principals

    return request.bound_data[reify_key]


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(object):
    # Callable that takes an object id and a permission and returns
    # a list of tuples (<object id>, <permission>).
    get_bound_permissions = None

    def permits(self, context, principals, permission):
        if permission == PRIVATE:
            return Authenticated in principals

        # Add prefixed user id to principals.
        prefixed_userid = context.get_prefixed_userid()
        if prefixed_userid and ':' in prefixed_userid:
            principals = principals + [prefixed_userid]
            prefix, user_id = prefixed_userid.split(':', 1)
            # Remove unprefixed user id to avoid conflicts.
            # (it is added via Pyramid Authn policy effective principals)
            if user_id in principals:
                principals.remove(user_id)
            # Retro-compatibility with cliquet 2.0 '_' user id prefixes.
            # Just in case it was used in permissions definitions.
            principals.append('%s_%s' % (prefix, user_id))

        if permission == DYNAMIC:
            permission = context.required_permission

        if permission == 'create':
            permission = '%s:%s' % (context.resource_name, permission)

        if context.allowed_principals:
            allowed = bool(set(context.allowed_principals) & set(principals))
        else:
            allowed = context.check_permission(
                permission,
                principals,
                get_bound_permissions=self.get_bound_permissions)

        # If not allowed on this collection, but some records are shared with
        # the current user, then authorize.
        # The ShareableResource class will take care of the filtering.
        is_list_operation = (context.on_collection and
                             'create' not in permission)
        if not allowed and is_list_operation:
            shared_records = context.fetch_shared_records(
                permission,
                principals,
                get_bound_permissions=self.get_bound_permissions)
            allowed = len(shared_records) > 0

        return allowed

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER


class RouteFactory(object):
    resource_name = None
    on_collection = False
    required_permission = None
    allowed_principals = None
    permission_object_id = None
    current_record = None
    get_shared_ids = None

    method_permissions = {
        "head": "read",
        "get": "read",
        "post": "create",
        "delete": "write",
        "patch": "write"
    }

    def __init__(self, request):
        # Make it available for the authorization policy.
        self.get_prefixed_userid = functools.partial(prefixed_userid, request)

        self._check_permission = request.registry.permission.check_permission

        # Partial collections of ShareableResource:
        self.shared_ids = []

        # Store service, resource, record and required permission.
        service = utils.current_service(request)

        is_on_resource = (service is not None and
                          hasattr(service, 'viewset') and
                          hasattr(service, 'resource'))

        if is_on_resource:
            self.on_collection = getattr(service, "type", None) == "collection"
            self.permission_object_id = self.get_permission_object_id(request)

            # Decide what the required unbound permission is depending on the
            # method that's being requested.
            if request.method.lower() == "put":
                # In the case of a "PUT", check if the targetted record already
                # exists, return "write" if it does, "create" otherwise.

                # If the view exists, use its collection to catch an
                # eventual NotFound.
                resource = service.resource(request=request, context=self)
                try:
                    record = resource.model.get_record(resource.record_id)
                    self.current_record = record
                except storage_exceptions.RecordNotFoundError:
                    self.permission_object_id = service.collection_path.format(
                        **request.matchdict)
                    self.required_permission = "create"
                else:
                    self.required_permission = "write"
            else:
                method = request.method.lower()
                self.required_permission = self.method_permissions.get(method)

            self.resource_name = request.current_resource_name

            if self.on_collection:
                object_id_match = self.get_permission_object_id(request, '*')
                self.get_shared_ids = functools.partial(
                    request.registry.permission.principals_accessible_objects,
                    object_id_match=object_id_match)

            settings = request.registry.settings
            setting = '%s_%s_principals' % (self.resource_name,
                                            self.required_permission)
            self.allowed_principals = aslist(settings.get(setting, ''))

    def check_permission(self, *args, **kw):
        return self._check_permission(self.permission_object_id, *args, **kw)

    def fetch_shared_records(self, perm, principals, get_bound_permissions):
        ids = self.get_shared_ids(
            permission=perm,
            principals=principals,
            get_bound_permissions=get_bound_permissions)
        # Store for later use in ``ShareableResource``.
        self.shared_ids = [self.extract_object_id(id_) for id_ in ids]
        return self.shared_ids

    def get_permission_object_id(self, request, record_id=None):
        record_uri = request.path

        if self.on_collection and record_id is not None:
            # With the current request on a collection, the record URI must
            # be found out by inspecting the collection service and its sibling
            # record service.
            service = request.current_service
            # XXX: Why not use service.path.format(id=) ?
            record_service = service.name.replace('-collection', '-record')
            matchdict = request.matchdict.copy()
            matchdict['id'] = record_id
            record_uri = request.route_path(record_service, **matchdict)

            if record_id == '*':
                record_uri = record_uri.replace('%2A', '*')

        return utils.strip_uri_prefix(record_uri)

    def extract_object_id(self, object_uri):
        # XXX: Help needed: use something like route.matchdict.get('id').
        return object_uri.split('/')[-1]
