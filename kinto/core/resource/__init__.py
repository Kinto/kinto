import logging
import re
import functools
from uuid import uuid4

import colander
import venusian

from pyramid import exceptions as pyramid_exceptions
from pyramid.decorator import reify
from pyramid.security import Everyone
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound, HTTPServiceUnavailable)

from kinto.core import Service
from kinto.core.errors import http_error, raise_invalid, send_alert, ERRORS, request_GET
from kinto.core.events import ACTIONS
from kinto.core.storage import exceptions as storage_exceptions, Filter, Sort
from kinto.core.utils import (
    COMPARISON, classname, decode64, encode64, json, find_nested_value,
    dict_subset, recursive_update_dict, apply_json_patch
)

from .model import Model, ShareableModel
from .schema import ResourceSchema, JsonPatchRequestSchema
from .viewset import ViewSet, ShareableViewSet


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


def register_resource(resource_cls, settings=None, viewset=None, depth=1,
                      **kwargs):
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
        """Registers a service in cornice, for the given type.
        """
        path_pattern = getattr(viewset, '{}_path'.format(endpoint_type))
        path_values = {'resource_name': resource_name}
        path = path_pattern.format_map(path_values)

        name = viewset.get_service_name(endpoint_type, resource_cls)

        service = Service(name, path, depth=depth,
                          **viewset.get_service_arguments())

        # Attach viewset and resource to the service for later reference.
        service.viewset = viewset
        service.resource = resource_cls
        service.type = endpoint_type
        # Attach collection and record paths.
        service.collection_path = viewset.collection_path.format_map(path_values)
        service.record_path = (viewset.record_path.format_map(path_values)
                               if viewset.record_path is not None else None)

        methods = getattr(viewset, '{}_methods'.format(endpoint_type))
        for method in methods:
            if not viewset.is_endpoint_enabled(
                    endpoint_type, resource_name, method.lower(), settings):
                continue

            argument_getter = getattr(viewset, '{}_arguments'.format(endpoint_type))
            view_args = argument_getter(resource_cls, method)

            view = viewset.get_view(endpoint_type, method.lower())
            service.add_view(method, view, klass=resource_cls, **view_args)

            # We support JSON-patch on PATCH views. Since the body payload
            # of JSON Patch is not a dict (mapping) but an array, we can't
            # use the same schema as for other PATCH protocols. We add another
            # dedicated view for PATCH, but targetting a different content_type
            # predicate.
            if method.lower() == "patch":
                view_args['content_type'] = "application/json-patch+json"
                view_args['schema'] = JsonPatchRequestSchema()
                service.add_view(method, view, klass=resource_cls, **view_args)

        return service

    def callback(context, name, ob):
        # get the callbacks registred by the inner services
        # and call them from here when the @resource classes are being
        # scanned by venusian.
        config = context.config.with_package(info.module)

        # Storage is mandatory for resources.
        if not hasattr(config.registry, 'storage'):
            msg = 'Mandatory storage backend is missing from configuration.'
            raise pyramid_exceptions.ConfigurationError(msg)

        # A service for the list.
        service = register_service('collection', config.registry.settings)
        config.add_cornice_service(service)
        # An optional one for record endpoint.
        if getattr(viewset, 'record_path') is not None:
            service = register_service('record', config.registry.settings)
            config.add_cornice_service(service)

    info = venusian.attach(resource_cls, callback, category='pyramid', depth=depth)
    return callback


class UserResource:
    """Base resource class providing every endpoint."""

    default_viewset = ViewSet
    """Default :class:`kinto.core.resource.viewset.ViewSet` class to use when
    the resource is registered."""

    default_model = Model
    """Default :class:`kinto.core.resource.model.Model` class to use for
    interacting the :mod:`kinto.core.storage` and :mod:`kinto.core.permission`
    backends."""

    schema = ResourceSchema
    """Schema to validate records."""

    def __init__(self, request, context=None):
        self.request = request
        self.context = context
        self.record_id = self.request.matchdict.get('id')
        self.force_patch_update = False

        content_type = str(self.request.headers.get('Content-Type')).lower()
        self._is_json_patch = content_type == 'application/json-patch+json'

        # Models are isolated by user.
        parent_id = self.get_parent_id(request)

        # Authentication to storage is transmitted as is (cf. cloud_storage).
        auth = request.headers.get('Authorization')

        self.model = self.default_model(
            storage=request.registry.storage,
            id_generator=self.id_generator,
            collection_id=classname(self),
            parent_id=parent_id,
            auth=auth)

        # Initialize timestamp as soon as possible.
        self.timestamp

    @reify
    def id_generator(self):
        # ID generator by resource name in settings.
        default_id_generator = self.request.registry.id_generators['']
        resource_name = self.request.current_resource_name
        id_generator = self.request.registry.id_generators.get(resource_name,
                                                               default_id_generator)
        return id_generator

    @reify
    def timestamp(self):
        """Return the current collection timestamp.

        :rtype: int
        """
        try:
            return self.model.timestamp()
        except storage_exceptions.BackendError as e:
            is_readonly = self.request.registry.settings['readonly']
            if not is_readonly:
                raise e
            # If the instance is configured to be readonly, and if the
            # collection is empty, the backend will try to bump the timestamp.
            # It fails if the configured db user has not write privileges.
            logger.exception(e)
            error_msg = ("Collection timestamp cannot be written. "
                         "Records endpoint must be hit at least once from a "
                         "writable instance.")
            raise http_error(HTTPServiceUnavailable(),
                             errno=ERRORS.BACKEND,
                             message=error_msg)

    def get_parent_id(self, request):
        """Return the parent_id of the resource with regards to the current
        request.

        :param request:
            The request used to create the resource.

        :rtype: str

        """
        return request.prefixed_userid

    def _get_known_fields(self):
        """Return all the `field` defined in the ressource schema."""
        known_fields = [c.name for c in self.schema().children] + \
                       [self.model.id_field,
                        self.model.modified_field,
                        self.model.deleted_field]
        return known_fields

    def is_known_field(self, field):
        """Return ``True`` if `field` is defined in the resource schema.
        If the resource schema allows unknown fields, this will always return
        ``True``.

        :param str field: Field name
        :rtype: bool

        """
        if self.schema.get_option('preserve_unknown'):
            return True

        known_fields = self._get_known_fields()
        # Test first level only: ``target.data.id`` -> ``target``
        field = field.split('.', 1)[0]
        return field in known_fields

    #
    # End-points
    #

    def collection_get(self):
        """Model ``GET`` endpoint: retrieve multiple records.

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
        self._add_timestamp_header(self.request.response)
        self._add_cache_header(self.request.response)
        self._raise_304_if_not_modified()
        # Collections are considered resources that always exist
        self._raise_412_if_modified(record={})

        headers = self.request.response.headers

        filters = self._extract_filters()
        limit = self._extract_limit()
        sorting = self._extract_sorting(limit)
        partial_fields = self._extract_partial_fields()

        filter_fields = [f.field for f in filters]
        include_deleted = self.model.modified_field in filter_fields

        pagination_rules, offset = self._extract_pagination_rules_from_token(
            limit, sorting)

        records, total_records = self.model.get_records(
            filters=filters,
            sorting=sorting,
            limit=limit,
            pagination_rules=pagination_rules,
            include_deleted=include_deleted)

        offset = offset + len(records)
        if limit and len(records) == limit and offset < total_records:
            lastrecord = records[-1]
            next_page = self._next_page_url(sorting, limit, lastrecord, offset)
            headers['Next-Page'] = next_page

        if partial_fields:
            records = [
                dict_subset(record, partial_fields)
                for record in records
            ]

        headers['Total-Records'] = str(total_records)

        return self.postprocess(records)

    def collection_post(self):
        """Model ``POST`` endpoint: create a record.

        If the new record id conflicts against an existing one, the
        posted record is ignored, and the existing record is returned, with
        a ``200`` status.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and collection modified
            in the iterim.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`kinto.core.resource.UserResource.process_record`
        """
        new_record = self.request.validated['body'].get('data', {})
        try:
            # Since ``id`` does not belong to schema, it is not in validated
            # data. Must look up in body.
            id_field = self.model.id_field
            new_record[id_field] = _id = self.request.json['data'][id_field]
            self._raise_400_if_invalid_id(_id)
            existing = self._get_record_or_404(_id)
        except (HTTPNotFound, KeyError, ValueError):
            existing = None

        self._raise_412_if_modified(record=existing)

        if existing:
            record = existing
            action = ACTIONS.READ
        else:
            new_record = self.process_record(new_record)
            record = self.model.create_record(new_record)
            self.request.response.status_code = 201
            action = ACTIONS.CREATE

        timestamp = record[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(record, action=action)

    def collection_delete(self):
        """Model ``DELETE`` endpoint: delete multiple records.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and collection modified
            in the iterim.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters are invalid.
        """
        # Collections are considered resources that always exist
        self._raise_412_if_modified(record={})

        filters = self._extract_filters()
        limit = self._extract_limit()
        sorting = self._extract_sorting(limit)
        pagination_rules, offset = self._extract_pagination_rules_from_token(limit, sorting)

        records, total_records = self.model.get_records(filters=filters,
                                                        sorting=sorting,
                                                        limit=limit,
                                                        pagination_rules=pagination_rules)
        deleted = self.model.delete_records(filters=filters,
                                            sorting=sorting,
                                            limit=limit,
                                            pagination_rules=pagination_rules)
        if deleted:
            lastrecord = deleted[-1]
            # Get timestamp of the last deleted field
            timestamp = lastrecord[self.model.modified_field]
            self._add_timestamp_header(self.request.response, timestamp=timestamp)

            # Add pagination header
            offset = offset + len(deleted)
            if limit and len(deleted) == limit and offset < total_records:
                next_page = self._next_page_url(sorting, limit, lastrecord, offset)
                self.request.response.headers['Next-Page'] = next_page
        else:
            self._add_timestamp_header(self.request.response)

        headers = self.request.response.headers
        headers['Total-Records'] = str(total_records)

        action = len(deleted) > 0 and ACTIONS.DELETE or ACTIONS.READ
        return self.postprocess(deleted, action=action, old=records)

    def get(self):
        """Record ``GET`` endpoint: retrieve a record.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified` if
            ``If-None-Match`` header is provided and record not
            modified in the interim.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and record modified
            in the iterim.
        """
        self._raise_400_if_invalid_id(self.record_id)
        record = self._get_record_or_404(self.record_id)
        timestamp = record[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)
        self._add_cache_header(self.request.response)
        self._raise_304_if_not_modified(record)
        self._raise_412_if_modified(record)

        partial_fields = self._extract_partial_fields()
        if partial_fields:
            record = dict_subset(record, partial_fields)

        return self.postprocess(record)

    def put(self):
        """Record ``PUT`` endpoint: create or replace the provided record and
        return it.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and record modified
            in the iterim.

        .. note::

            If ``If-None-Match: *`` request header is provided, the
            ``PUT`` will succeed only if no record exists with this id.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`kinto.core.resource.UserResource.process_record`.
        """
        self._raise_400_if_invalid_id(self.record_id)
        try:
            existing = self._get_record_or_404(self.record_id)
        except HTTPNotFound:
            existing = None

        self._raise_412_if_modified(record=existing)

        # If `data` is not provided, use existing record (or empty if creation)
        post_record = self.request.validated['body'].get('data', existing) or {}

        record_id = post_record.setdefault(self.model.id_field, self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(post_record, old=existing)

        if existing:
            record = self.model.update_record(new_record)
        else:
            record = self.model.create_record(new_record)
            self.request.response.status_code = 201

        timestamp = record[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        action = existing and ACTIONS.UPDATE or ACTIONS.CREATE
        return self.postprocess(record, action=action, old=existing)

    def patch(self):
        """Record ``PATCH`` endpoint: modify a record and return its
        new version.

        If a request header ``Response-Behavior`` is set to ``light``,
        only the fields whose value was changed are returned.
        If set to ``diff``, only the fields whose value became different than
        the one provided are returned.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and record modified
            in the iterim.

        .. seealso::
            Add custom behaviour by overriding
            :meth:`kinto.core.resource.UserResource.apply_changes` or
            :meth:`kinto.core.resource.UserResource.process_record`.
        """
        self._raise_400_if_invalid_id(self.record_id)
        existing = self._get_record_or_404(self.record_id)
        self._raise_412_if_modified(existing)

        # patch is specified as a list of of operations (RFC 6902)
        if self._is_json_patch:
            requested_changes = self.request.validated['body']
        else:
            # `data` attribute may not be present if only perms are patched.
            body = self.request.validated['body']
            if not body:
                # If no `data` nor `permissions` is provided in patch, reject!
                # XXX: This should happen in schema instead (c.f. ShareableViewSet)
                error_details = {
                    'name': 'data',
                    'description': 'Provide at least one of data or permissions',
                }
                raise_invalid(self.request, **error_details)
            requested_changes = body.get('data', {})

        updated, applied_changes = self.apply_changes(existing,
                                                      requested_changes=requested_changes)

        record_id = updated.setdefault(self.model.id_field,
                                       self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(updated, old=existing)

        changed_fields = [k for k in applied_changes.keys()
                          if existing.get(k) != new_record.get(k)]

        # Save in storage if necessary.
        if changed_fields or self.force_patch_update:
            new_record = self.model.update_record(new_record)

        else:
            # Behave as if storage would have added `id` and `last_modified`.
            for extra_field in [self.model.modified_field,
                                self.model.id_field]:
                new_record[extra_field] = existing[extra_field]

        # Adjust response according to ``Response-Behavior`` header
        body_behavior = self.request.validated['header'].get('Response-Behavior', 'full')

        if body_behavior.lower() == 'light':
            # Only fields that were changed.
            data = {k: new_record[k] for k in changed_fields}

        elif body_behavior.lower() == 'diff':
            # Only fields that are different from those provided.
            data = {k: new_record[k] for k in changed_fields
                    if applied_changes.get(k) != new_record.get(k)}
        else:
            data = new_record

        timestamp = new_record.get(self.model.modified_field,
                                   existing[self.model.modified_field])
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(data, action=ACTIONS.UPDATE, old=existing)

    def delete(self):
        """Record ``DELETE`` endpoint: delete a record and return it.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and record modified
            in the iterim.
        """
        self._raise_400_if_invalid_id(self.record_id)
        record = self._get_record_or_404(self.record_id)
        self._raise_412_if_modified(record)

        # Retreive the last_modified information from a querystring if present.
        last_modified = self.request.validated['querystring'].get('last_modified')

        # If less or equal than current record. Ignore it.
        if last_modified and last_modified <= record[self.model.modified_field]:
            last_modified = None

        deleted = self.model.delete_record(record, last_modified=last_modified)
        timestamp = deleted[self.model.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(deleted, action=ACTIONS.DELETE, old=record)

    #
    # Data processing
    #

    def process_record(self, new, old=None):
        """Hook for processing records before they reach storage, to introduce
        specific logics on fields for example.

        .. code-block:: python

            def process_record(self, new, old=None):
                new = super().process_record(new, old)
                version = old['version'] if old else 0
                new['version'] = version + 1
                return new

        Or add extra validation based on request:

        .. code-block:: python

            from kinto.core.errors import raise_invalid

            def process_record(self, new, old=None):
                new = super().process_record(new, old)
                if new['browser'] not in request.headers['User-Agent']:
                    raise_invalid(self.request, name='browser', error='Wrong')
                return new

        :param dict new: the validated record to be created or updated.
        :param dict old: the old record to be updated,
            ``None`` for creation endpoints.

        :returns: the processed record.
        :rtype: dict
        """
        modified_field = self.model.modified_field
        new_last_modified = new.get(modified_field)

        # Drop the new last_modified if it is not an integer.
        is_integer = isinstance(new_last_modified, int)
        if not is_integer:
            new.pop(modified_field, None)
            return new

        # Drop the new last_modified if lesser or equal to the old one.
        is_less_or_equal = (old is not None and
                            new_last_modified <= old[modified_field])
        if is_less_or_equal:
            new.pop(modified_field, None)

        return new

    def apply_changes(self, record, requested_changes):
        """Merge `changes` into `record` fields.

        .. note::

            This is used in the context of PATCH only.

        Override this to control field changes at record level, for example:

        .. code-block:: python

            def apply_changes(self, record, requested_changes):
                # Ignore value change if inferior
                if record['position'] > changes.get('position', -1):
                    changes.pop('position', None)
                return super().apply_changes(record, requested_changes)

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if result does not comply with resource schema.

        :returns: the new record with `changes` applied.
        :rtype: tuple
        """
        if self._is_json_patch:
            try:
                applied_changes = apply_json_patch(record, requested_changes)['data']
                updated = {**applied_changes}
            except ValueError as e:
                error_details = {
                    'location': 'body',
                    'description': 'JSON Patch operation failed: {}'.format(e)
                }
                raise_invalid(self.request, **error_details)

        else:
            applied_changes = {**requested_changes}
            updated = {**record}

            content_type = str(self.request.headers.get('Content-Type')).lower()
            # recursive patch and remove field if null attribute is passed (RFC 7396)
            if content_type == 'application/merge-patch+json':
                recursive_update_dict(updated, applied_changes, ignores=[None])
            else:
                updated.update(**applied_changes)

        for field, value in applied_changes.items():
            has_changed = record.get(field, value) != value
            if self.schema.is_readonly(field) and has_changed:
                error_details = {
                    'name': field,
                    'description': 'Cannot modify {}'.format(field)
                }
                raise_invalid(self.request, **error_details)

        try:
            validated = self.schema().deserialize(updated)
        except colander.Invalid as e:
            # Transform the errors we got from colander into Cornice errors.
            # We could not rely on Service schema because the record should be
            # validated only once the changes are applied
            for field, error in e.asdict().items():  # pragma: no branch
                raise_invalid(self.request, name=field, description=error)

        return validated, applied_changes

    def postprocess(self, result, action=ACTIONS.READ, old=None):
        body = {
            'data': result
        }

        parent_id = self.get_parent_id(self.request)
        self.request.notify_resource_event(parent_id=parent_id,
                                           timestamp=self.timestamp,
                                           data=result,
                                           action=action,
                                           old=old)

        return body

    #
    # Internals
    #

    def _get_record_or_404(self, record_id):
        """Retrieve record from storage and raise ``404 Not found`` if missing.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.
        """
        if self.context and self.context.current_record:
            # Set during authorization. Save a storage hit.
            return self.context.current_record

        try:
            return self.model.get_record(record_id)
        except storage_exceptions.RecordNotFoundError:
            details = {
                "id": record_id,
                "resource_name": self.request.current_resource_name
            }
            response = http_error(HTTPNotFound(), errno=ERRORS.INVALID_RESOURCE_ID,
                                  details=details)
            raise response

    def _add_timestamp_header(self, response, timestamp=None):
        """Add current timestamp in response headers, when request comes in.

        """
        if timestamp is None:
            timestamp = self.timestamp
        # Pyramid takes care of converting.
        response.last_modified = timestamp / 1000.0
        # Return timestamp as ETag.
        response.headers['ETag'] = '"{}"'.format(timestamp)

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
        resource_name = self.context.resource_name if self.context else ''
        setting_key = '{}_cache_expires_seconds'.format(resource_name)
        collection_expires = self.request.registry.settings.get(setting_key)
        is_anonymous = self.request.prefixed_userid is None
        if collection_expires and is_anonymous:
            response.cache_expires(seconds=int(collection_expires))
        else:
            # Since `Expires` response header provides an HTTP data with a
            # resolution in seconds, do not use Pyramid `cache_expires()` in
            # order to omit it.
            response.cache_control.no_cache = True
            response.cache_control.no_store = True

    def _raise_400_if_invalid_id(self, record_id):
        """Raise 400 if specified record id does not match the format excepted
        by storage backends.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        is_string = isinstance(record_id, str)
        if not is_string or not self.model.id_generator.match(record_id):
            error_details = {
                'location': 'path',
                'description': "Invalid record id"
            }
            raise_invalid(self.request, **error_details)

    def _raise_304_if_not_modified(self, record=None):
        """Raise 304 if current timestamp is inferior to the one specified
        in headers.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified`
        """
        if_none_match = self.request.validated['header'].get('If-None-Match')

        if not if_none_match:
            return

        if if_none_match == '*':
            return

        if record:
            current_timestamp = record[self.model.modified_field]
        else:
            current_timestamp = self.model.timestamp()

        if current_timestamp == if_none_match:
            response = HTTPNotModified()
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_412_if_modified(self, record=None):
        """Raise 412 if current timestamp is superior to the one
        specified in headers.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed`
        """
        if_match = self.request.validated['header'].get('If-Match')
        if_none_match = self.request.validated['header'].get('If-None-Match')

        # Check if record exists
        record_exists = record is not None

        # If no precondition headers, just ignore
        if not if_match and not if_none_match:
            return

        # If-None-Match: * should always raise if a record exists
        if if_none_match == '*' and record_exists:
            modified_since = -1  # Always raise.

        # If-Match should always raise if a record doesn't exist
        elif if_match and not record_exists:
            modified_since = -1

        # If-Match with ETag value on existing records should compare ETag
        elif if_match and if_match != '*':
            modified_since = if_match

        # If none of the above applies, don't raise
        else:
            return

        if record:
            current_timestamp = record[self.model.modified_field]
        else:
            current_timestamp = self.model.timestamp()

        if current_timestamp != modified_since:
            error_msg = 'Resource was modified meanwhile'
            details = {'existing': record} if record else {}
            response = http_error(HTTPPreconditionFailed(),
                                  errno=ERRORS.MODIFIED_MEANWHILE,
                                  message=error_msg,
                                  details=details)
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_400_if_id_mismatch(self, new_id, record_id):
        """Raise 400 if the `new_id`, within the request body, does not match
        the `record_id`, obtained from request path.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        if new_id != record_id:
            error_msg = 'Record id does not match existing record'
            error_details = {
                'name': self.model.id_field,
                'description': error_msg
            }
            raise_invalid(self.request, **error_details)

    def _extract_partial_fields(self):
        """Extract the fields to do the projection from QueryString parameters.
        """
        fields = self.request.validated['querystring'].get('_fields')
        if fields:
            root_fields = [f.split('.')[0] for f in fields]
            known_fields = self._get_known_fields()
            invalid_fields = set(root_fields) - set(known_fields)
            preserve_unknown = self.schema.get_option('preserve_unknown')
            if not preserve_unknown and invalid_fields:
                error_msg = "Fields {} do not exist".format(','.join(invalid_fields))
                error_details = {
                    'name': "Invalid _fields parameter",
                    'description': error_msg
                }
                raise_invalid(self.request, **error_details)

            # Since id and last_modified are part of the synchronisation
            # API, force their presence in payloads.
            fields = fields + [self.model.id_field, self.model.modified_field]

        return fields

    def _extract_limit(self):
        """Extract limit value from QueryString parameters."""
        paginate_by = self.request.registry.settings['paginate_by']
        max_fetch_size = self.request.registry.settings['storage_max_fetch_size']
        limit = self.request.validated['querystring'].get('_limit', paginate_by)

        # If limit is higher than paginate_by setting, ignore it.
        if limit and paginate_by:
            limit = min(limit, paginate_by)

        # If limit is higher than what storage can retrieve, ignore it.
        limit = min(limit, max_fetch_size) if limit else max_fetch_size

        return limit

    def _extract_filters(self):
        """Extracts filters from QueryString parameters."""
        queryparams = self.request.validated['querystring']

        filters = []

        for param, value in queryparams.items():
            param = param.strip()

            error_details = {
                'name': param,
                'location': 'querystring',
                'description': 'Invalid value for {}'.format(param)
            }

            # Ignore specific fields
            if param.startswith('_') and param not in ('_since',
                                                       '_to',
                                                       '_before'):
                continue

            # Handle the _since specific filter.
            if param in ('_since', '_to', '_before'):

                if param == '_since':
                    operator = COMPARISON.GT
                else:
                    if param == '_to':
                        message = ('_to is now deprecated, '
                                   'you should use _before instead')
                        url = ('https://kinto.readthedocs.io/en/2.4.0/api/'
                               'resource.html#list-of-available-url-'
                               'parameters')
                        send_alert(self.request, message, url)
                    operator = COMPARISON.LT
                filters.append(
                    Filter(self.model.modified_field, value, operator)
                )
                continue

            allKeywords = '|'.join([i.name.lower() for i in COMPARISON])
            m = re.match(r'^('+allKeywords+')_([\w\.]+)$', param)
            if m:
                keyword, field = m.groups()
                operator = getattr(COMPARISON, keyword.upper())
            else:
                operator, field = COMPARISON.EQ, param

            if not self.is_known_field(field):
                error_msg = "Unknown filter field '{}'".format(param)
                error_details['description'] = error_msg
                raise_invalid(self.request, **error_details)

            if operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                all_integers = all([isinstance(v, int)
                                    for v in value])
                all_strings = all([isinstance(v, str)
                                   for v in value])
                has_invalid_value = (
                    (field == self.model.id_field and not all_strings) or
                    (field == self.model.modified_field and not all_integers)
                )
                if has_invalid_value:
                    raise_invalid(self.request, **error_details)

            filters.append(Filter(field, value, operator))

        return filters

    def _extract_sorting(self, limit):
        """Extracts filters from QueryString parameters."""
        specified = self.request.validated['querystring'].get('_sort', [])
        sorting = []
        modified_field_used = self.model.modified_field in specified
        for field in specified:
            field = field.strip()
            m = re.match(r'^([\-+]?)([\w\.]+)$', field)
            if m:
                order, field = m.groups()

                if not self.is_known_field(field):
                    error_details = {
                        'location': 'querystring',
                        'description': "Unknown sort field '{}'".format(field)
                    }
                    raise_invalid(self.request, **error_details)

                direction = -1 if order == '-' else 1
                sorting.append(Sort(field, direction))

        if not modified_field_used:
            # Add a sort by the ``modified_field`` in descending order
            # useful for pagination
            sorting.append(Sort(self.model.modified_field, -1))
        return sorting

    def _build_pagination_rules(self, sorting, last_record, rules=None):
        """Return the list of rules for a given sorting attribute and
        last_record.

        """
        if rules is None:
            rules = []

        rule = []
        next_sorting = sorting[:-1]

        for field, _ in next_sorting:
            rule.append(Filter(field, last_record.get(field), COMPARISON.EQ))

        field, direction = sorting[-1]

        if direction == -1:
            rule.append(Filter(field, last_record.get(field), COMPARISON.LT))
        else:
            rule.append(Filter(field, last_record.get(field), COMPARISON.GT))

        rules.append(rule)

        if len(next_sorting) == 0:
            return rules

        return self._build_pagination_rules(next_sorting, last_record, rules)

    def _extract_pagination_rules_from_token(self, limit, sorting):
        """Get pagination params."""
        token = self.request.validated['querystring'].get('_token', None)
        filters = []
        offset = 0
        if token:
            error_msg = None
            try:
                tokeninfo = json.loads(decode64(token))
                if not isinstance(tokeninfo, dict):
                    raise ValueError()
                last_record = tokeninfo['last_record']
                offset = tokeninfo['offset']
                nonce = tokeninfo['nonce']
            except (ValueError, KeyError, TypeError):
                error_msg = '_token has invalid content'

            # We don't want pagination tokens to be reused several times (#1171).
            # The cache backend is used to keep track of "nonces".
            if self.request.method.lower() == "delete" and error_msg is None:
                registry = self.request.registry
                deleted = registry.cache.delete(nonce)
                if deleted is None:
                    error_msg = '_token was already used or has expired.'

            if error_msg:
                error_details = {
                    'location': 'querystring',
                    'description': error_msg
                }
                raise_invalid(self.request, **error_details)

            filters = self._build_pagination_rules(sorting, last_record)

        return filters, offset

    def _next_page_url(self, sorting, limit, last_record, offset):
        """Build the Next-Page header from where we stopped."""
        token = self._build_pagination_token(sorting, last_record, offset)

        params = {**request_GET(self.request), '_limit': limit, '_token': token}

        service = self.request.current_service
        next_page_url = self.request.route_url(service.name, _query=params,
                                               **self.request.matchdict)
        return next_page_url

    def _build_pagination_token(self, sorting, last_record, offset):
        """Build a pagination token.

        It is a base64 JSON object with the sorting fields values of
        the last_record.

        """
        nonce = "pagination-token-{}".format(uuid4())
        if self.request.method.lower() == "delete":
            registry = self.request.registry
            validity = registry.settings["pagination_token_validity_seconds"]
            registry.cache.set(nonce, "", validity)

        token = {
            'last_record': {},
            'offset': offset,
            'nonce': nonce,
        }

        for field, _ in sorting:
            last_value = find_nested_value(last_record, field)
            if last_value is not None:
                token['last_record'][field] = last_value

        return encode64(json.dumps(token))


class ShareableResource(UserResource):
    """Shareable resources allow to set permissions on records, in order to
    share their access or protect their modification.
    """
    default_model = ShareableModel
    default_viewset = ShareableViewSet
    permissions = ('read', 'write')
    """List of allowed permissions names."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # In base resource, PATCH only hit storage if no data has changed.
        # Here, we force update because we add the current principal to
        # the ``write`` ACE.
        self.force_patch_update = True

        # Required by the ShareableModel class.
        self.model.permission = self.request.registry.permission
        if self.request.prefixed_userid is None:
            # The principal of an anonymous is system.Everyone
            self.model.current_principal = Everyone
        else:
            self.model.current_principal = self.request.prefixed_userid
        self.model.prefixed_principals = self.request.prefixed_principals

        if self.context:
            self.model.get_permission_object_id = functools.partial(
                self.context.get_permission_object_id,
                self.request)

    def get_parent_id(self, request):
        """Unlike :class:`kinto.core.resource.UserResource`, records are not
        isolated by user.

        See https://github.com/mozilla-services/cliquet/issues/549

        :returns: A constant empty value.
        """
        return ''

    def _extract_filters(self):
        """Override default filters extraction from QueryString to allow
        partial collection of records.

        XXX: find more elegant approach to add custom filters.
        """
        filters = super()._extract_filters()

        ids = self.context.shared_ids
        if ids is not None:
            filter_by_id = Filter(self.model.id_field, ids, COMPARISON.IN)
            filters.insert(0, filter_by_id)

        return filters

    def _raise_412_if_modified(self, record=None):
        """Do not provide the permissions among the record fields.
        Ref: https://github.com/Kinto/kinto/issues/224
        """
        if record:
            record = {**record}
            record.pop(self.model.permissions_field, None)
        return super()._raise_412_if_modified(record)

    def process_record(self, new, old=None):
        """Read permissions from request body, and in the case of ``PUT`` every
        existing ACE is removed (using empty list).
        """
        new = super().process_record(new, old)

        # patch is specified as a list of of operations (RFC 6902)
        if self._is_json_patch:
            changes = self.request.validated['body']
            permissions = apply_json_patch(old, changes)['permissions']
        else:
            permissions = self.request.validated['body'].get('permissions', {})

        annotated = {**new}

        if permissions:
            is_put = (self.request.method.lower() == 'put')
            if is_put:
                # Remove every existing ACEs using empty lists.
                for perm in self.permissions:
                    permissions.setdefault(perm, [])
            annotated[self.model.permissions_field] = permissions

        return annotated

    def postprocess(self, result, action=ACTIONS.READ, old=None):
        """Add ``permissions`` attribute in response body.

        In the HTTP API, it was decided that ``permissions`` would reside
        outside the ``data`` attribute.
        """
        body = {}

        if not isinstance(result, list):
            # record endpoint.
            perms = result.pop(self.model.permissions_field, None)
            if perms is not None:
                body['permissions'] = {k: list(p) for k, p in perms.items()}

            if old:
                # Remove permissions from event payload.
                old.pop(self.model.permissions_field, None)

        data = super().postprocess(result, action, old)
        body.update(data)
        return body
