import functools
import logging
import re
import warnings
from uuid import uuid4

import colander
import venusian
from pyramid import exceptions as pyramid_exceptions
from pyramid.authorization import Everyone
from pyramid.decorator import reify
from pyramid.httpexceptions import (
    HTTPNotFound,
    HTTPNotModified,
    HTTPPreconditionFailed,
    HTTPServiceUnavailable,
)
from pyramid.settings import asbool

from kinto.core import Service
from kinto.core.errors import ERRORS, http_error, raise_invalid, request_GET, send_alert
from kinto.core.events import ACTIONS
from kinto.core.storage import MISSING, Filter, Sort
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.utils import (
    COMPARISON,
    apply_json_patch,
    classname,
    decode64,
    dict_subset,
    encode64,
    find_nested_value,
    json,
    recursive_update_dict,
)

from .model import Model
from .schema import JsonPatchRequestSchema, ResourceSchema
from .viewset import ViewSet

logger = logging.getLogger(__name__)


def register(depth=1, **kwargs):
    """Ressource class decorator.

    Register the decorated class in the cornice registry.
    Pass all its keyword arguments to the register_resource
    function.
    """

    def wrapped(resource):
        register_resource(resource, depth=depth + 1, **kwargs)
        return resource

    return wrapped


def register_resource(resource_cls, settings=None, viewset=None, depth=1, **kwargs):
    """Register a resource in the cornice registry.

    :param resource_cls:
        The resource class to register.
        It should be a class or have a "name" attribute.

    :param viewset:
        A ViewSet object, which will be used to find out which arguments should
        be appended to the views, and where the views are.

    :param depth:
        A depth offset. It will be used to determine what is the level of depth
        in the call tree. (set to 1 by default.)

    Any additional keyword parameters will be used to override the viewset
    attributes.
    """
    if viewset is None:
        viewset = resource_cls.default_viewset(**kwargs)
    else:
        viewset.update(**kwargs)

    resource_name = viewset.get_name(resource_cls)

    def register_service(endpoint_type, settings):
        """Registers a service in cornice, for the given type."""
        path_pattern = getattr(viewset, f"{endpoint_type}_path")
        path_values = {"resource_name": resource_name}
        path = path_pattern.format_map(path_values)

        name = viewset.get_service_name(endpoint_type, resource_cls)

        service = Service(name, path, depth=depth, **viewset.get_service_arguments())

        # Attach viewset and resource to the service for later reference.
        service.viewset = viewset
        service.resource = resource_cls
        service.type = endpoint_type
        # Attach plural and object paths.
        service.plural_path = viewset.plural_path.format_map(path_values)
        service.object_path = (
            viewset.object_path.format_map(path_values)
            if viewset.object_path is not None
            else None
        )

        methods = getattr(viewset, f"{endpoint_type}_methods")
        for method in methods:
            if not viewset.is_endpoint_enabled(
                endpoint_type, resource_name, method.lower(), settings
            ):
                continue

            argument_getter = getattr(viewset, f"{endpoint_type}_arguments")
            view_args = argument_getter(resource_cls, method)

            view = viewset.get_view(endpoint_type, method.lower())
            service.add_view(method, view, klass=resource_cls, **view_args)

            # We support JSON-patch on PATCH views. Since the body payload
            # of JSON Patch is not a dict (mapping) but an array, we can't
            # use the same schema as for other PATCH protocols. We add another
            # dedicated view for PATCH, but targetting a different content_type
            # predicate.
            if method.lower() == "patch":
                view_args["content_type"] = "application/json-patch+json"
                view_args["schema"] = JsonPatchRequestSchema()
                service.add_view(method, view, klass=resource_cls, **view_args)

        return service

    def callback(context, name, ob):
        # get the callbacks registred by the inner services
        # and call them from here when the @resource classes are being
        # scanned by venusian.
        config = context.config.with_package(info.module)

        # Storage is mandatory for resources.
        if not hasattr(config.registry, "storage"):
            msg = "Mandatory storage backend is missing from configuration."
            raise pyramid_exceptions.ConfigurationError(msg)

        # A service for the list.
        service = register_service("plural", config.registry.settings)
        config.add_cornice_service(service)
        # An optional one for object endpoint.
        if getattr(viewset, "object_path") is not None:
            service = register_service("object", config.registry.settings)
            config.add_cornice_service(service)

    info = venusian.attach(resource_cls, callback, category="pyramid", depth=depth)
    return callback


class Resource:
    """Resource class providing every HTTP endpoint.

    A resource provides all the necessary mechanism for:
    - storage and retrieval of objects according to HTTP verbs
    - permission checking and tracking
    - concurrency control
    - synchronization
    - OpenAPI metadata

    Permissions are verified in :class:`kinto.core.authorization.AuthorizationPolicy` based on the
    verb and context (eg. a put can create or update). The resulting context
    is passed in the `context` constructor parameter.
    """

    default_viewset = ViewSet
    """Default :class:`kinto.core.resource.viewset.ViewSet` class to use when
    the resource is registered."""

    default_model = Model
    """Default :class:`kinto.core.resource.model.Model` class to use for
    interacting the :mod:`kinto.core.storage` and :mod:`kinto.core.permission`
    backends."""

    schema = ResourceSchema
    """Schema to validate objects."""

    permissions = ("read", "write")
    """List of allowed permissions names."""

    def __init__(self, request, context=None):
        """
        :param request:
            The current request object.
        :param context:
            The resulting context obtained from :class:`kinto.core.authorization.AuthorizationPolicy`.
        """
        self.request = request
        self.context = context

        content_type = str(self.request.headers.get("Content-Type")).lower()
        self._is_json_patch = content_type == "application/json-patch+json"
        self._is_merge_patch = content_type == "application/merge-patch+json"

        # Models are isolated by user.
        parent_id = self.get_parent_id(request)

        # The principal of an anonymous is system.Everyone
        current_principal = self.request.prefixed_userid or Everyone

        if not hasattr(self, "model"):
            self.model = self.default_model(
                storage=request.registry.storage,
                permission=request.registry.permission,
                id_generator=self.id_generator,
                resource_name=classname(self),
                parent_id=parent_id,
                current_principal=current_principal,
                prefixed_principals=request.prefixed_principals,
                explicit_perm=asbool(request.registry.settings["explicit_permissions"]),
            )

        # Initialize timestamp as soon as possible.
        self.timestamp

        if self.context:
            self.model.get_permission_object_id = functools.partial(
                self.context.get_permission_object_id, self.request
            )

    @reify
    def id_generator(self):
        # ID generator by resource name in settings.
        default_id_generator = self.request.registry.id_generators[""]
        resource_name = self.request.current_resource_name
        id_generator = self.request.registry.id_generators.get(resource_name, default_id_generator)
        return id_generator

    @reify
    def timestamp(self):
        """Return the current resource timestamp.

        :rtype: int
        """
        try:
            return self.model.timestamp()
        except storage_exceptions.ReadonlyError as e:
            # If the instance is configured to be readonly, and if the
            # resource is empty, the backend will try to bump the timestamp.
            # It fails if the configured db user has not write privileges.
            logger.exception(e)
            error_msg = (
                "Resource timestamp cannot be written. "
                "Plural endpoint must be hit at least once from a "
                "writable instance."
            )
            raise http_error(HTTPServiceUnavailable(), errno=ERRORS.BACKEND, message=error_msg)

    @reify
    def object_id(self):
        """Return the object id for this request. It's either in the match dict
        or in the posted body.
        """
        if self.request.method.lower() == "post":
            try:
                # Since ``id`` does not belong to schema, it is not in validated
                # data. Must look up in body directly instead of request.validated.
                _id = self.request.json["data"][self.model.id_field]
                self._raise_400_if_invalid_id(_id)
                return _id
            except (KeyError, ValueError):
                return None
        return self.request.matchdict.get("id")

    def get_parent_id(self, request):
        """Return the parent_id of the resource with regards to the current
        request.

        The resource will isolate the objects from one parent id to another.
        For example, in Kinto, the ``group``s and ``collection``s are isolated by ``bucket``.

        In order to obtain a resource where users can only see their own objects, just
        return the user id as the parent id:

        .. code-block:: python

            def get_parent_id(self, request):
                return request.prefixed_userid

        :param request:
            The request used to access the resource.

        :rtype: str
        """
        return ""

    def _get_known_fields(self):
        """Return all the `field` defined in the ressource schema."""
        known_fields = [c.name for c in self.schema().children] + [
            self.model.id_field,
            self.model.modified_field,
            self.model.deleted_field,
        ]
        return known_fields

    def is_known_field(self, field):
        """Return ``True`` if `field` is defined in the resource schema.
        If the resource schema allows unknown fields, this will always return
        ``True``.

        :param str field: Field name
        :rtype: bool

        """
        if self.schema.get_option("preserve_unknown"):
            return True

        known_fields = self._get_known_fields()
        # Test first level only: ``target.data.id`` -> ``target``
        field = field.split(".", 1)[0]
        return field in known_fields

    #
    # End-points
    #

    def plural_head(self):
        """Model ``HEAD`` endpoint: empty reponse with a ``Total-Objects`` header.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified` if
            ``If-None-Match`` header is provided and collection not
            modified in the interim.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and collection modified
            in the iterim.
        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters or sorting are invalid.
        """
        return self._plural_get(True)

    def plural_get(self):
        """Model ``GET`` endpoint: retrieve multiple objects.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified` if
            ``If-None-Match`` header is provided and the objects not
            modified in the interim.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and the objects modified
            in the iterim.
        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters or sorting are invalid.
        """
        return self._plural_get(False)

    def _plural_get(self, head_request):
        self._add_timestamp_header(self.request.response)
        self._add_cache_header(self.request.response)
        self._raise_304_if_not_modified()
        # Plural endpoints are considered resources that always exist
        self._raise_412_if_modified(obj={})

        headers = self.request.response.headers

        filters = self._extract_filters()
        limit = self._extract_limit()
        sorting = self._extract_sorting(limit)
        partial_fields = self._extract_partial_fields()

        filter_fields = [f.field for f in filters]
        include_deleted = self.model.modified_field in filter_fields

        pagination_rules, offset = self._extract_pagination_rules_from_token(limit, sorting)

        # The reason why we call self.model.get_objects() with `limit=limit + 1` is to avoid
        # having to count the total number of objects in the database just to be able
        # to *decide* whether or not to have a `Next-Page` header.
        # This way, we can quickly depend on the number of objects returned and compare that
        # with what the client requested.
        # For example, if there are 100 objects in the database and the client used limit=100,
        # it would, internally, ask for 101 objects. So if you retrieved 100 objects
        # it means we got less than we asked for and thus there is not another page.
        # Equally, if there are 200 objects in the database and the client used
        # limit=100 it would, internally, ask for 101 objects and actually get that. Then,
        # you know there is another page.

        if head_request:
            count = self.model.count_objects(filters=filters)
            headers["Total-Objects"] = headers["Total-Records"] = str(count)
            return self.postprocess([])

        objects = self.model.get_objects(
            filters=filters,
            sorting=sorting,
            limit=limit + 1,  # See bigger explanation above.
            pagination_rules=pagination_rules,
            include_deleted=include_deleted,
        )

        offset = offset + len(objects)

        if limit and len(objects) == limit + 1:
            lastobject = objects[-2]
            next_page = self._next_page_url(sorting, limit, lastobject, offset)
            headers["Next-Page"] = next_page

        if partial_fields:
            objects = [dict_subset(obj, partial_fields) for obj in objects]

        # See bigger explanation above about the use of limits. The need for slicing
        # here is because we might have asked for 1 more object just to see if there's
        # a next page. But we have to honor the limit in our returned response.
        return self.postprocess(objects[:limit])

    def plural_post(self):
        """Model ``POST`` endpoint: create an object.

        If the new object id conflicts against an existing one, the
        posted object is ignored, and the existing object is returned, with
        a ``200`` status.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and the objects modified
            in the iterim.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`kinto.core.resource.Resource.process_object`
        """
        new_object = self.request.validated["body"].get("data", {})

        existing = None
        # If id was specified, then add it to posted body and look-up
        # the existing object.
        if self.object_id is not None:
            new_object[self.model.id_field] = self.object_id
            try:
                existing = self._get_object_or_404(self.object_id)
            except HTTPNotFound:
                pass

        self._raise_412_if_modified(obj=existing)

        if existing:
            obj = existing
            action = ACTIONS.READ
        else:
            new_object = self.process_object(new_object)
            obj = self.model.create_object(new_object)
            self.request.response.status_code = 201
            action = ACTIONS.CREATE

        timestamp = obj[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(obj, action=action)

    def plural_delete(self):
        """Model ``DELETE`` endpoint: delete multiple objects.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and the objects modified
            in the iterim.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters are invalid.
        """
        # Plural endpoint are considered resources that always exist
        self._raise_412_if_modified(obj={})

        filters = self._extract_filters()
        limit = self._extract_limit()
        sorting = self._extract_sorting(limit)
        pagination_rules, offset = self._extract_pagination_rules_from_token(limit, sorting)

        objects = self.model.get_objects(
            filters=filters, sorting=sorting, limit=limit + 1, pagination_rules=pagination_rules
        )
        deleted = self.model.delete_objects(
            filters=filters, sorting=sorting, limit=limit, pagination_rules=pagination_rules
        )
        if deleted:
            lastobject = deleted[-1]
            # Add pagination header, but only if there are more objects beyond the limit.
            if limit and len(objects) == limit + 1:
                next_page = self._next_page_url(sorting, limit, lastobject, offset)
                self.request.response.headers["Next-Page"] = next_page

            timestamp = max({d[self.model.modified_field] for d in deleted})
            self._add_timestamp_header(self.request.response, timestamp=timestamp)

        else:
            self._add_timestamp_header(self.request.response)

        action = len(deleted) > 0 and ACTIONS.DELETE or ACTIONS.READ
        return self.postprocess(deleted, action=action, old=objects[:limit])

    def get(self):
        """Object ``GET`` endpoint: retrieve an object.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the object is not found.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified` if
            ``If-None-Match`` header is provided and object not
            modified in the interim.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and object modified
            in the iterim.
        """
        self._raise_400_if_invalid_id(self.object_id)
        obj = self._get_object_or_404(self.object_id)
        timestamp = obj[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)
        self._add_cache_header(self.request.response)
        self._raise_304_if_not_modified(obj)
        self._raise_412_if_modified(obj)

        partial_fields = self._extract_partial_fields()
        if partial_fields:
            obj = dict_subset(obj, partial_fields)

        return self.postprocess(obj)

    def put(self):
        """Object ``PUT`` endpoint: create or replace the provided object and
        return it.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and object modified
            in the iterim.

        .. note::

            If ``If-None-Match: *`` request header is provided, the
            ``PUT`` will succeed only if no object exists with this id.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`kinto.core.resource.Resource.process_object`.
        """
        self._raise_400_if_invalid_id(self.object_id)
        try:
            existing = self._get_object_or_404(self.object_id)
        except HTTPNotFound:
            existing = None

        self._raise_412_if_modified(obj=existing)

        # If `data` is not provided, use existing object (or empty if creation)
        post_object = self.request.validated["body"].get("data", existing) or {}

        object_id = post_object.setdefault(self.model.id_field, self.object_id)
        self._raise_400_if_id_mismatch(object_id, self.object_id)

        new_object = self.process_object(post_object, old=existing)

        if existing:
            obj = self.model.update_object(new_object)
        else:
            obj = self.model.create_object(new_object)
            self.request.response.status_code = 201

        timestamp = obj[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        action = existing and ACTIONS.UPDATE or ACTIONS.CREATE
        return self.postprocess(obj, action=action, old=existing)

    def patch(self):
        """Object ``PATCH`` endpoint: modify an object and return its
        new version.

        If a request header ``Response-Behavior`` is set to ``light``,
        only the fields whose value was changed are returned.
        If set to ``diff``, only the fields whose value became different than
        the one provided are returned.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the object is not found.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and object modified
            in the iterim.

        .. seealso::
            Add custom behaviour by overriding
            :meth:`kinto.core.resource.Resource.apply_changes` or
            :meth:`kinto.core.resource.Resource.process_object`.
        """
        self._raise_400_if_invalid_id(self.object_id)
        existing = self._get_object_or_404(self.object_id)
        self._raise_412_if_modified(existing)

        # patch is specified as a list of of operations (RFC 6902)
        if self._is_json_patch:
            requested_changes = self.request.validated["body"]
        else:
            # `data` attribute may not be present if only perms are patched.
            body = self.request.validated["body"]
            if not body:
                # If no `data` nor `permissions` is provided in patch, reject!
                # XXX: This should happen in schema instead (c.f. ViewSet)
                error_details = {
                    "name": "data",
                    "description": "Provide at least one of data or permissions",
                }
                raise_invalid(self.request, **error_details)
            requested_changes = body.get("data", {})

        updated, applied_changes = self.apply_changes(
            obj=existing, requested_changes=requested_changes
        )

        object_id = updated.setdefault(self.model.id_field, self.object_id)
        self._raise_400_if_id_mismatch(object_id, self.object_id)

        new_object = self.process_object(updated, old=existing)

        changed_fields = [
            k for k in applied_changes.keys() if existing.get(k) != new_object.get(k)
        ]

        new_object = self.model.update_object(new_object)

        # Adjust response according to ``Response-Behavior`` header
        body_behavior = self.request.validated["header"].get("Response-Behavior", "full")

        if body_behavior.lower() == "light":
            # Only fields that were changed.
            data = {k: new_object[k] for k in changed_fields}

        elif body_behavior.lower() == "diff":
            # Only fields that are different from those provided.
            data = {
                k: new_object[k]
                for k in changed_fields
                if applied_changes.get(k) != new_object.get(k)
            }
        else:
            data = new_object

        timestamp = new_object.get(self.model.modified_field, existing[self.model.modified_field])
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(data, action=ACTIONS.UPDATE, old=existing)

    def delete(self):
        """Object ``DELETE`` endpoint: delete an object and return it.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the object is not found.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and object modified
            in the iterim.
        """
        self._raise_400_if_invalid_id(self.object_id)
        obj = self._get_object_or_404(self.object_id)
        self._raise_412_if_modified(obj)

        # Retreive the last_modified information from a querystring if present.
        last_modified = self.request.validated["querystring"].get("last_modified")

        # If less or equal than current object. Ignore it.
        if last_modified and last_modified <= obj[self.model.modified_field]:
            last_modified = None

        try:
            deleted = self.model.delete_object(obj, last_modified=last_modified)
        except storage_exceptions.ObjectNotFoundError:
            # Delete might fail if the object was deleted since we
            # fetched it from the storage (ref Kinto/kinto#1407). This
            # is one of a larger class of issues where another request
            # could modify the object between our fetch and our
            # delete, which could e.g. invalidate our precondition
            # checking. Fixing this correctly is a larger
            # problem. However, let's punt on fixing it correctly and
            # just handle this one important case for now (see #1557).
            #
            # Raise a 404 vs. a 409 or 412 because that's what we
            # would have done if the other thread's delete had
            # happened a little earlier. (The client doesn't need to
            # know that we did a bunch of work fetching the existing
            # object for nothing.)
            raise self._404_for_object(self.object_id)

        timestamp = deleted[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(deleted, action=ACTIONS.DELETE, old=obj)

    #
    # Data processing
    #

    def process_object(self, new, old=None):
        """Hook for processing objects before they reach storage, to introduce
        specific logics on fields for example.

        .. code-block:: python

            def process_object(self, new, old=None):
                new = super().process_object(new, old)
                version = old['version'] if old else 0
                new['version'] = version + 1
                return new

        Or add extra validation based on request:

        .. code-block:: python

            from kinto.core.errors import raise_invalid

            def process_object(self, new, old=None):
                new = super().process_object(new, old)
                if new['browser'] not in request.headers['User-Agent']:
                    raise_invalid(self.request, name='browser', error='Wrong')
                return new

        :param dict new: the validated object to be created or updated.
        :param dict old: the old object to be updated,
            ``None`` for creation endpoints.

        :returns: the processed object.
        :rtype: dict
        """
        modified_field = self.model.modified_field
        new_last_modified = new.get(modified_field)

        # Drop the new last_modified if it is not an integer.
        is_integer = isinstance(new_last_modified, int)
        if not is_integer:
            new.pop(modified_field, None)
            new_last_modified = None

        # Drop the new last_modified if lesser or equal to the old one.
        is_less_or_equal = (
            new_last_modified and old is not None and new_last_modified <= old[modified_field]
        )
        if is_less_or_equal:
            new.pop(modified_field, None)

        # patch is specified as a list of of operations (RFC 6902)

        payload = self.request.validated["body"]

        if self._is_json_patch:
            permissions = apply_json_patch(old, payload)["permissions"]

        elif self._is_merge_patch:
            existing = old or {}
            permissions = existing.get("__permissions__", {})
            recursive_update_dict(permissions, payload.get("permissions", {}), ignores=(None,))

        else:
            permissions = {
                k: v for k, v in payload.get("permissions", {}).items() if v is not None
            }

        annotated = {**new}

        if permissions:
            is_put = self.request.method.lower() == "put"
            if is_put or self._is_merge_patch:
                # Remove every existing ACEs using empty lists.
                for perm in self.permissions:
                    permissions.setdefault(perm, [])
            annotated[self.model.permissions_field] = permissions

        return annotated

    def apply_changes(self, obj, requested_changes):
        """Merge `changes` into `object` fields.

        .. note::

            This is used in the context of PATCH only.

        Override this to control field changes at object level, for example:

        .. code-block:: python

            def apply_changes(self, obj, requested_changes):
                # Ignore value change if inferior
                if object['position'] > changes.get('position', -1):
                    changes.pop('position', None)
                return super().apply_changes(obj, requested_changes)

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if result does not comply with resource schema.

        :returns: the new object with `changes` applied.
        :rtype: tuple
        """
        if self._is_json_patch:
            try:
                applied_changes = apply_json_patch(obj, requested_changes)["data"]
                updated = {**applied_changes}
            except ValueError as e:
                error_details = {
                    "location": "body",
                    "description": f"JSON Patch operation failed: {e}",
                }
                raise_invalid(self.request, **error_details)

        else:
            applied_changes = {**requested_changes}
            updated = {**obj}

            # recursive patch and remove field if null attribute is passed (RFC 7396)
            if self._is_merge_patch:
                recursive_update_dict(updated, applied_changes, ignores=(None,))
            else:
                updated.update(**applied_changes)

        for field, value in applied_changes.items():
            has_changed = obj.get(field, value) != value
            if self.schema.is_readonly(field) and has_changed:
                error_details = {"name": field, "description": f"Cannot modify {field}"}
                raise_invalid(self.request, **error_details)

        try:
            validated = self.schema().deserialize(updated)
        except colander.Invalid as e:
            # Transform the errors we got from colander into Cornice errors.
            # We could not rely on Service schema because the object should be
            # validated only once the changes are applied
            for field, error in e.asdict().items():  # pragma: no branch
                raise_invalid(self.request, name=field, description=error)

        return validated, applied_changes

    def postprocess(self, result, action=ACTIONS.READ, old=None):
        body = {}

        if not isinstance(result, list):
            perms = result.pop(self.model.permissions_field, None)
            if perms is not None:
                body["permissions"] = {k: list(p) for k, p in perms.items()}
            if old:
                # Remove permissions from event payload.
                old.pop(self.model.permissions_field, None)

        body["data"] = result

        parent_id = self.get_parent_id(self.request)
        # Use self.model.timestamp() instead of self.timestamp because
        # self.timestamp is @reify'd relatively early in the request,
        # so doesn't correspond to any time that is relevant to the
        # event. See #1769.
        timestamp = self.model.timestamp()
        self.request.notify_resource_event(
            parent_id=parent_id, timestamp=timestamp, data=result, action=action, old=old
        )

        return body

    #
    # Internals
    #

    def _404_for_object(self, object_id):
        details = {"id": object_id, "resource_name": self.request.current_resource_name}
        return http_error(HTTPNotFound(), errno=ERRORS.INVALID_RESOURCE_ID, details=details)

    def _get_object_or_404(self, object_id):
        """Retrieve object from storage and raise ``404 Not found`` if missing.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the object is not found.
        """
        if self.context and self.context.current_object:
            # Set during authorization. Save a storage hit.
            return self.context.current_object

        try:
            return self.model.get_object(object_id)
        except storage_exceptions.ObjectNotFoundError:
            raise self._404_for_object(object_id)

    def _add_timestamp_header(self, response, timestamp=None):
        """Add current timestamp in response headers, when request comes in."""
        if timestamp is None:
            timestamp = self.timestamp
        # Pyramid takes care of converting.
        response.last_modified = timestamp / 1000.0
        # Return timestamp as ETag.
        response.headers["ETag"] = f'"{timestamp}"'

    def _add_cache_header(self, response):
        """Add Cache-Control and Expire headers, based a on a setting for the
        current resource.

        Cache headers will be set with anonymous requests only.

        .. note::

            The ``Cache-Control: no-cache`` response header does not prevent
            caching in client. It will indicate the client to revalidate
            the response content on each access. The client will send a
            conditional request to the server and check that a
            ``304 Not modified`` is returned before serving content from cache.
        """
        resource_name = self.context.resource_name if self.context else ""
        setting_key = f"{resource_name}_cache_expires_seconds"
        cache_expires = self.request.registry.settings.get(setting_key)
        is_anonymous = self.request.prefixed_userid is None
        if cache_expires and is_anonymous:
            response.cache_expires(seconds=int(cache_expires))
        else:
            # Since `Expires` response header provides an HTTP data with a
            # resolution in seconds, do not use Pyramid `cache_expires()` in
            # order to omit it.
            response.cache_control.no_cache = True
            response.cache_control.no_store = True

    def _raise_400_if_invalid_id(self, object_id):
        """Raise 400 if specified object id does not match the format excepted
        by storage backends.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        is_string = isinstance(object_id, str)
        if not is_string or not self.model.id_generator.match(object_id):
            error_details = {"location": "path", "description": "Invalid object id"}
            raise_invalid(self.request, **error_details)

    def _raise_304_if_not_modified(self, obj=None):
        """Raise 304 if current timestamp is inferior to the one specified
        in headers.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified`
        """
        if_none_match = self.request.validated["header"].get("If-None-Match")

        if not if_none_match:
            return

        if if_none_match == "*":
            return

        if obj:
            current_timestamp = obj[self.model.modified_field]
        else:
            current_timestamp = self.model.timestamp()

        if current_timestamp == if_none_match:
            response = HTTPNotModified()
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_412_if_modified(self, obj=None):
        """Raise 412 if current timestamp is superior to the one
        specified in headers.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed`
        """
        if_match = self.request.validated["header"].get("If-Match")
        if_none_match = self.request.validated["header"].get("If-None-Match")

        # Check if object exists
        object_exists = obj is not None

        # If no precondition headers, just ignore
        if not if_match and not if_none_match:
            return

        # If-None-Match: * should always raise if an object exists
        if if_none_match == "*" and object_exists:
            modified_since = -1  # Always raise.

        # If-Match should always raise if an object doesn't exist
        elif if_match and not object_exists:
            modified_since = -1

        # If-Match with ETag value on existing objects should compare ETag
        elif if_match and if_match != "*":
            modified_since = if_match

        # If none of the above applies, don't raise
        else:
            return

        if obj:
            current_timestamp = obj[self.model.modified_field]
        else:
            current_timestamp = self.model.timestamp()

        if current_timestamp != modified_since:
            error_msg = "Resource was modified meanwhile"
            # Do not provide the permissions among the object fields.
            # Ref: https://github.com/Kinto/kinto/issues/224
            existing = {**obj} if obj else {}
            existing.pop(self.model.permissions_field, None)

            details = {"existing": existing} if obj else {}
            response = http_error(
                HTTPPreconditionFailed(),
                errno=ERRORS.MODIFIED_MEANWHILE,
                message=error_msg,
                details=details,
            )
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_400_if_id_mismatch(self, new_id, object_id):
        """Raise 400 if the `new_id`, within the request body, does not match
        the `object_id`, obtained from request path.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        if new_id != object_id:
            error_msg = "Object id does not match existing object"
            error_details = {"name": self.model.id_field, "description": error_msg}
            raise_invalid(self.request, **error_details)

    def _extract_partial_fields(self):
        """Extract the fields to do the projection from QueryString parameters."""
        fields = self.request.validated["querystring"].get("_fields")
        if fields:
            root_fields = [f.split(".")[0] for f in fields]
            known_fields = self._get_known_fields()
            invalid_fields = set(root_fields) - set(known_fields)
            preserve_unknown = self.schema.get_option("preserve_unknown")
            if not preserve_unknown and invalid_fields:
                error_msg = f"Fields {','.join(invalid_fields)} do not exist"
                error_details = {"name": "Invalid _fields parameter", "description": error_msg}
                raise_invalid(self.request, **error_details)

            # Since id and last_modified are part of the synchronisation
            # API, force their presence in payloads.
            fields = fields + [self.model.id_field, self.model.modified_field]

        return fields

    def _extract_limit(self):
        """Extract limit value from QueryString parameters."""
        paginate_by = self.request.registry.settings["paginate_by"]
        max_fetch_size = self.request.registry.settings["storage_max_fetch_size"]
        limit = self.request.validated["querystring"].get("_limit", paginate_by)

        # If limit is higher than paginate_by setting, ignore it.
        if limit and paginate_by:
            limit = min(limit, paginate_by)

        # If limit is higher than what storage can retrieve, ignore it.
        limit = min(limit, max_fetch_size) if limit else max_fetch_size

        return limit

    def _extract_filters(self):
        """Extracts filters from QueryString parameters."""
        queryparams = self.request.validated["querystring"]

        filters = []

        for param, value in queryparams.items():
            param = param.strip()

            error_details = {
                "name": param,
                "location": "querystring",
                "description": f"Invalid value for {param}",
            }

            # Ignore specific fields
            if param.startswith("_") and param not in ("_since", "_to", "_before"):
                continue

            # Handle the _since specific filter.
            if param in ("_since", "_to", "_before"):

                if param == "_since":
                    operator = COMPARISON.GT
                else:
                    if param == "_to":
                        message = "_to is now deprecated, " "you should use _before instead"
                        url = (
                            "https://kinto.readthedocs.io/en/2.4.0/api/"
                            "resource.html#list-of-available-url-"
                            "parameters"
                        )
                        send_alert(self.request, message, url)
                    operator = COMPARISON.LT

                if value == "" or not isinstance(value, (int, str, type(None))):
                    raise_invalid(self.request, **error_details)

                filters.append(Filter(self.model.modified_field, value, operator))
                continue

            all_keywords = r"|".join([i.name.lower() for i in COMPARISON])
            m = re.match(r"^(" + all_keywords + r")_([\w\.]+)$", param)
            if m:
                keyword, field = m.groups()
                operator = getattr(COMPARISON, keyword.upper())
            else:
                operator, field = COMPARISON.EQ, param

            if not self.is_known_field(field):
                error_msg = f"Unknown filter field '{param}'"
                error_details["description"] = error_msg
                raise_invalid(self.request, **error_details)

            # Return 400 if _limit is not a string
            if operator == COMPARISON.LIKE:
                if not isinstance(value, str):
                    raise_invalid(self.request, **error_details)

            if operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                all_integers = all([isinstance(v, int) for v in value])
                all_strings = all([isinstance(v, str) for v in value])
                has_invalid_value = (field == self.model.id_field and not all_strings) or (
                    field == self.model.modified_field and not all_integers
                )
                if has_invalid_value:
                    raise_invalid(self.request, **error_details)

            if "\x00" in field or "\x00" in str(value):
                error_details["description"] = "Invalid character 0x00"
                raise_invalid(self.request, **error_details)

            if field == self.model.modified_field and value == "":
                raise_invalid(self.request, **error_details)

            filters.append(Filter(field, value, operator))

        # If a plural endpoint is reached, and if the user does not have the
        # permission to read/write the whole list, the set is filtered by ids,
        # based on the list of ids returned by the authorization policy.
        ids = self.context.shared_ids
        if ids is not None:
            filter_by_id = Filter(self.model.id_field, ids, COMPARISON.IN)
            filters.insert(0, filter_by_id)

        return filters

    def _extract_sorting(self, limit):
        """Extracts filters from QueryString parameters."""
        specified = self.request.validated["querystring"].get("_sort", [])
        sorting = []
        modified_field_used = self.model.modified_field in specified
        for field in specified:
            field = field.strip()
            m = re.match(r"^([\-+]?)([\w\.]+)$", field)
            if m:
                order, field = m.groups()

                if not self.is_known_field(field):
                    error_details = {
                        "location": "querystring",
                        "description": f"Unknown sort field '{field}'",
                    }
                    raise_invalid(self.request, **error_details)

                direction = -1 if order == "-" else 1
                sorting.append(Sort(field, direction))

        if not modified_field_used:
            # Add a sort by the ``modified_field`` in descending order
            # useful for pagination
            sorting.append(Sort(self.model.modified_field, -1))
        return sorting

    def _build_pagination_rules(self, sorting, last_object, rules=None):
        """Return the list of rules for a given sorting attribute and
        last_object.

        """
        if rules is None:
            rules = []

        rule = []
        next_sorting = sorting[:-1]

        for field, _ in next_sorting:
            rule.append(Filter(field, last_object.get(field, MISSING), COMPARISON.EQ))

        field, direction = sorting[-1]

        if direction == -1:
            rule.append(Filter(field, last_object.get(field, MISSING), COMPARISON.LT))
        else:
            rule.append(Filter(field, last_object.get(field, MISSING), COMPARISON.GT))

        rules.append(rule)

        if len(next_sorting) == 0:
            return rules

        return self._build_pagination_rules(next_sorting, last_object, rules)

    def _extract_pagination_rules_from_token(self, limit, sorting):
        """Get pagination params."""
        token = self.request.validated["querystring"].get("_token", None)
        filters = []
        offset = 0
        if token:
            error_msg = None
            try:
                tokeninfo = json.loads(decode64(token))
                if not isinstance(tokeninfo, dict):
                    raise ValueError()
                last_object = tokeninfo["last_object"]
                offset = tokeninfo["offset"]
                nonce = tokeninfo["nonce"]
            except (ValueError, KeyError, TypeError):
                error_msg = "_token has invalid content"

            # We don't want pagination tokens to be reused several times (#1171).
            # The cache backend is used to keep track of "nonces".
            if self.request.method.lower() == "delete" and error_msg is None:
                registry = self.request.registry
                deleted = registry.cache.delete(nonce)
                if deleted is None:
                    error_msg = "_token was already used or has expired."

            if error_msg:
                error_details = {"location": "querystring", "description": error_msg}
                raise_invalid(self.request, **error_details)

            filters = self._build_pagination_rules(sorting, last_object)

        return filters, offset

    def _next_page_url(self, sorting, limit, last_object, offset):
        """Build the Next-Page header from where we stopped."""
        token = self._build_pagination_token(sorting, last_object, offset)

        params = {**request_GET(self.request), "_limit": limit, "_token": token}

        service = self.request.current_service
        next_page_url = self.request.route_url(
            service.name, _query=params, **self.request.matchdict
        )
        return next_page_url

    def _build_pagination_token(self, sorting, last_object, offset):
        """Build a pagination token.

        It is a base64 JSON object with the sorting fields values of
        the last_object.

        """
        nonce = f"pagination-token-{uuid4()}"
        if self.request.method.lower() == "delete":
            registry = self.request.registry
            validity = registry.settings["pagination_token_validity_seconds"]
            registry.cache.set(nonce, "", validity)

        token = {"last_object": {}, "offset": offset, "nonce": nonce}

        for field, _ in sorting:
            last_value = find_nested_value(last_object, field, MISSING)
            if last_value is not MISSING:
                token["last_object"][field] = last_value

        return encode64(json.dumps(token))

    @property
    def record_id(self):
        message = "`record_id` is deprecated, use `object_id` instead."
        warnings.warn(message, DeprecationWarning)
        return self.object_id

    def process_record(self, *args, **kwargs):
        message = "`process_record()` is deprecated, use `process_object()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.process_object(*args, **kwargs)

    def collection_get(self, *args, **kwargs):
        message = "`collection_get()` is deprecated, use `plural_get()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.plural_get(*args, **kwargs)

    def collection_post(self, *args, **kwargs):
        message = "`collection_post()` is deprecated, use `plural_post()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.plural_post(*args, **kwargs)

    def collection_delete(self, *args, **kwargs):
        message = "`collection_delete()` is deprecated, use `plural_delete()` instead."
        warnings.warn(message, DeprecationWarning)
        return self.plural_delete(*args, **kwargs)


class ShareableResource(Resource):
    def __init__(self, *args, **kwargs):
        message = "`ShareableResource` is deprecated, use `Resource` instead."
        warnings.warn(message, DeprecationWarning)
        super().__init__(*args, **kwargs)
