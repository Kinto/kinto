import re
import functools
import warnings

import colander
import venusian
import six
from pyramid import exceptions as pyramid_exceptions
from pyramid.decorator import reify
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound, HTTPConflict,
                                    HTTPServiceUnavailable)

from kinto.core import logger
from kinto.core import Service
from kinto.core.errors import http_error, raise_invalid, send_alert, ERRORS
from kinto.core.events import ACTIONS
from kinto.core.storage import exceptions as storage_exceptions, Filter, Sort
from kinto.core.utils import (
    COMPARISON, classname, native_value, decode64, encode64, json,
    encode_header, decode_header, DeprecatedMeta, dict_subset
)

from .model import Model, ShareableModel
from .schema import ResourceSchema
from .viewset import ViewSet, ShareableViewSet


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

    path_formatters = {
        'resource_name': resource_name
    }

    def register_service(endpoint_type, settings):
        """Registers a service in cornice, for the given type."""
        path_pattern = getattr(viewset, '%s_path' % endpoint_type)
        path = path_pattern.format(**path_formatters)

        name = viewset.get_service_name(endpoint_type, resource_cls)

        service = Service(name, path, depth=depth,
                          **viewset.get_service_arguments())

        # Attach viewset and resource to the service for later reference.
        service.viewset = viewset
        service.resource = resource_cls
        service.collection_path = viewset.collection_path.format(
            **path_formatters)
        service.record_path = viewset.record_path.format(**path_formatters)
        service.type = endpoint_type

        methods = getattr(viewset, '%s_methods' % endpoint_type)
        for method in methods:
            if not viewset.is_endpoint_enabled(
                    endpoint_type, resource_name, method.lower(), settings):
                continue

            argument_getter = getattr(viewset, '%s_arguments' % endpoint_type)
            view_args = argument_getter(resource_cls, method)

            view = viewset.get_view(endpoint_type, method.lower())
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

        services = [register_service('collection', config.registry.settings),
                    register_service('record', config.registry.settings)]
        for service in services:
            config.add_cornice_service(service)

    info = venusian.attach(resource_cls, callback, category='pyramid',
                           depth=depth)
    return callback


class UserResource(object):
    """Base resource class providing every endpoint."""

    default_viewset = ViewSet
    """Default :class:`kinto.core.viewset.ViewSet` class to use when the resource
    is registered."""

    default_model = Model
    """Default :class:`kinto.core.resource.model.Model` class to use for
    interacting the :mod:`kinto.core.storage` and :mod:`kinto.core.permission`
    backends."""

    mapping = ResourceSchema()
    """Schema to validate records."""

    def __init__(self, request, context=None):
        # Models are isolated by user.
        parent_id = self.get_parent_id(request)

        # Authentication to storage is transmitted as is (cf. cloud_storage).
        auth = request.headers.get('Authorization')

        self.model = self.default_model(
            storage=request.registry.storage,
            id_generator=request.registry.id_generator,
            collection_id=classname(self),
            parent_id=parent_id,
            auth=auth)

        self.request = request
        self.context = context
        self.record_id = self.request.matchdict.get('id')
        self.force_patch_update = False

        # Log resource context.
        logger.bind(collection_id=self.model.collection_id,
                    collection_timestamp=self.timestamp)

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

    @property
    def collection(self):
        """The collection property."""
        message = ('``self.collection`` is now deprecated. '
                   'Please use ``self.model`` instead')
        warnings.warn(message, DeprecationWarning)
        return self.model

    def get_parent_id(self, request):
        """Return the parent_id of the resource with regards to the current
        request.

        :param request:
            The request used to create the resource.

        :rtype: str

        """
        return request.prefixed_userid

    def _get_known_fields(self):
        """Return all the `field` defined in the ressource mapping."""
        known_fields = [c.name for c in self.mapping.children] + \
                       [self.model.id_field,
                        self.model.modified_field,
                        self.model.deleted_field]
        return known_fields

    def is_known_field(self, field):
        """Return ``True`` if `field` is defined in the resource mapping.

        :param str field: Field name
        :rtype: bool

        """
        known_fields = self._get_known_fields()
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
        self._raise_412_if_modified()

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
        next_page = None

        if limit and len(records) == limit and offset < total_records:
            lastrecord = records[-1]
            next_page = self._next_page_url(sorting, limit, lastrecord, offset)
            headers['Next-Page'] = encode_header(next_page)

        if partial_fields:
            records = [
                dict_subset(record, partial_fields)
                for record in records
            ]

        # Bind metric about response size.
        logger.bind(nb_records=len(records), limit=limit)
        headers['Total-Records'] = encode_header('%s' % total_records)

        return self.postprocess(records)

    def collection_post(self):
        """Model ``POST`` endpoint: create a record.

        If the new record conflicts against a unique field constraint, the
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
        existing = None
        new_record = self.request.validated['data']
        try:
            id_field = self.model.id_field
            # Since ``id`` does not belong to schema, look up in body.
            new_record[id_field] = _id = self.request.json['data'][id_field]
            self._raise_400_if_invalid_id(_id)
            existing = self._get_record_or_404(_id)
        except (HTTPNotFound, KeyError, ValueError):
            pass

        self._raise_412_if_modified(record=existing)

        new_record = self.process_record(new_record)
        try:
            unique_fields = self.mapping.get_option('unique_fields')
            record = self.model.create_record(new_record,
                                              unique_fields=unique_fields)
            self.request.response.status_code = 201
            action = ACTIONS.CREATE
        except storage_exceptions.UnicityError as e:
            record = e.record
            # failed to write
            action = ACTIONS.READ

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
        self._raise_412_if_modified()

        filters = self._extract_filters()
        deleted = self.model.delete_records(filters=filters)

        action = len(deleted) > 0 and ACTIONS.DELETE or ACTIONS.READ
        return self.postprocess(deleted, action=action)

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
        id_field = self.model.id_field
        existing = None
        tombstones = None
        try:
            existing = self._get_record_or_404(self.record_id)
        except HTTPNotFound:
            # Look if this record used to exist (for preconditions check).
            filter_by_id = Filter(id_field, self.record_id, COMPARISON.EQ)
            tombstones, _ = self.model.get_records(filters=[filter_by_id],
                                                   include_deleted=True)
            if len(tombstones) > 0:
                existing = tombstones[0]
        finally:
            if existing:
                self._raise_412_if_modified(existing)

        post_record = self.request.validated['data']

        record_id = post_record.setdefault(id_field, self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(post_record, old=existing)

        try:
            unique = self.mapping.get_option('unique_fields')
            if existing and not tombstones:
                record = self.model.update_record(new_record,
                                                  unique_fields=unique)
            else:
                record = self.model.create_record(new_record,
                                                  unique_fields=unique)
                self.request.response.status_code = 201
        except storage_exceptions.UnicityError as e:
            self._raise_conflict(e)

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

        try:
            # `data` attribute may not be present if only perms are patched.
            changes = self.request.json.get('data', {})
        except ValueError:
            # If no `data` nor `permissions` is provided in patch, reject!
            # XXX: This should happen in schema instead (c.f. ShareableViewSet)
            error_details = {
                'name': 'data',
                'description': 'Provide at least one of data or permissions',
            }
            raise_invalid(self.request, **error_details)

        updated = self.apply_changes(existing, changes=changes)

        record_id = updated.setdefault(self.model.id_field,
                                       self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(updated, old=existing)

        changed_fields = [k for k in changes.keys()
                          if existing.get(k) != new_record.get(k)]

        # Save in storage if necessary.
        if changed_fields or self.force_patch_update:
            try:
                unique_fields = self.mapping.get_option('unique_fields')
                new_record = self.model.update_record(
                    new_record,
                    unique_fields=unique_fields)
            except storage_exceptions.UnicityError as e:
                self._raise_conflict(e)
        else:
            # Behave as if storage would have added `id` and `last_modified`.
            for extra_field in [self.model.modified_field,
                                self.model.id_field]:
                new_record[extra_field] = existing[extra_field]

        # Adjust response according to ``Response-Behavior`` header
        body_behavior = self.request.headers.get('Response-Behavior', 'full')

        if body_behavior.lower() == 'light':
            # Only fields that were changed.
            data = {k: new_record[k] for k in changed_fields}

        elif body_behavior.lower() == 'diff':
            # Only fields that are different from those provided.
            data = {k: new_record[k] for k in changed_fields
                    if changes.get(k) != new_record.get(k)}
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
        last_modified = self.request.GET.get('last_modified')
        if last_modified:
            last_modified = native_value(last_modified.strip('"'))
            if not isinstance(last_modified, six.integer_types):
                error_details = {
                    'name': 'last_modified',
                    'location': 'querystring',
                    'description': 'Invalid value for %s' % last_modified
                }
                raise_invalid(self.request, **error_details)

            # If less or equal than current record. Ignore it.
            if last_modified <= record[self.model.modified_field]:
                last_modified = None

        deleted = self.model.delete_record(record, last_modified=last_modified)
        return self.postprocess(deleted, action=ACTIONS.DELETE)

    #
    # Data processing
    #

    def process_record(self, new, old=None):
        """Hook for processing records before they reach storage, to introduce
        specific logics on fields for example.

        .. code-block:: python

            def process_record(self, new, old=None):
                new = super(MyResource, self).process_record(new, old)
                version = old['version'] if old else 0
                new['version'] = version + 1
                return new

        Or add extra validation based on request:

        .. code-block:: python

            from kinto.core.errors import raise_invalid

            def process_record(self, new, old=None):
                new = super(MyResource, self).process_record(new, old)
                if new['browser'] not in request.headers['User-Agent']:
                    raise_invalid(self.request, name='browser', error='Wrong')
                return new

        :param dict new: the validated record to be created or updated.
        :param dict old: the old record to be updated,
            ``None`` for creation endpoints.

        :returns: the processed record.
        :rtype: dict
        """
        new_last_modified = new.get(self.model.modified_field)
        not_specified = old is None or self.model.modified_field not in old

        if new_last_modified is None or not_specified:
            return new

        # Drop the new last_modified if lesser or equal to the old one.
        is_less_or_equal = new_last_modified <= old[self.model.modified_field]
        if new_last_modified and is_less_or_equal:
            del new[self.model.modified_field]

        return new

    def apply_changes(self, record, changes):
        """Merge `changes` into `record` fields.

        .. note::

            This is used in the context of PATCH only.

        Override this to control field changes at record level, for example:

        .. code-block:: python

            def apply_changes(self, record, changes):
                # Ignore value change if inferior
                if record['position'] > changes.get('position', -1):
                    changes.pop('position', None)
                return super(MyResource, self).apply_changes(record, changes)

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if result does not comply with resource schema.

        :returns: the new record with `changes` applied.
        :rtype: dict
        """
        for field, value in changes.items():
            has_changed = record.get(field, value) != value
            if self.mapping.is_readonly(field) and has_changed:
                error_details = {
                    'name': field,
                    'description': 'Cannot modify {0}'.format(field)
                }
                raise_invalid(self.request, **error_details)

        updated = record.copy()
        updated.update(**changes)

        try:
            return self.mapping.deserialize(updated)
        except colander.Invalid as e:
            # Transform the errors we got from colander into Cornice errors.
            # We could not rely on Service schema because the record should be
            # validated only once the changes are applied
            for field, error in e.asdict().items():
                raise_invalid(self.request, name=field, description=error)

    def postprocess(self, result, action=ACTIONS.READ, old=None):
        body = {
            'data': result
        }

        self.request.notify_resource_event(timestamp=self.timestamp,
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
            response = http_error(HTTPNotFound(),
                                  errno=ERRORS.INVALID_RESOURCE_ID)
            raise response

    def _add_timestamp_header(self, response, timestamp=None):
        """Add current timestamp in response headers, when request comes in.

        """
        if timestamp is None:
            timestamp = self.timestamp
        # Pyramid takes care of converting.
        response.last_modified = timestamp / 1000.0
        # Return timestamp as ETag.
        response.headers['ETag'] = encode_header('"%s"' % timestamp)

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
        setting_key = '%s_cache_expires_seconds' % resource_name
        collection_expires = self.request.registry.settings.get(setting_key)
        is_anonymous = self.request.prefixed_userid is None
        if collection_expires and is_anonymous:
            response.cache_expires(seconds=int(collection_expires))
        else:
            # Since `Expires` response header provides an HTTP data with a
            # resolution in seconds, do not use Pyramid `cache_expires()` in
            # order to omit it.
            response.cache_control.no_cache = True

    def _raise_400_if_invalid_id(self, record_id):
        """Raise 400 if specified record id does not match the format excepted
        by storage backends.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        if not self.model.id_generator.match(six.text_type(record_id)):
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
        if_none_match = self.request.headers.get('If-None-Match')

        if not if_none_match:
            return

        if_none_match = decode_header(if_none_match)

        try:
            if not (if_none_match[0] == if_none_match[-1] == '"'):
                raise ValueError()
            modified_since = int(if_none_match[1:-1])
        except (IndexError, ValueError):
            if if_none_match == '*':
                return
            error_details = {
                'location': 'headers',
                'description': "Invalid value for If-None-Match"
            }
            raise_invalid(self.request, **error_details)

        if record:
            current_timestamp = record[self.model.modified_field]
        else:
            current_timestamp = self.model.timestamp()

        if current_timestamp <= modified_since:
            response = HTTPNotModified()
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_412_if_modified(self, record=None):
        """Raise 412 if current timestamp is superior to the one
        specified in headers.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed`
        """
        if_match = self.request.headers.get('If-Match')
        if_none_match = self.request.headers.get('If-None-Match')

        if not if_match and not if_none_match:
            return

        if_match = decode_header(if_match) if if_match else None

        if record and if_none_match and decode_header(if_none_match) == '*':
            if record.get(self.model.deleted_field, False):
                # Tombstones should not prevent creation.
                return
            modified_since = -1  # Always raise.
        elif if_match:
            try:
                if not (if_match[0] == if_match[-1] == '"'):
                    raise ValueError()
                modified_since = int(if_match[1:-1])
            except (IndexError, ValueError):
                message = ("Invalid value for If-Match. The value should "
                           "be integer between double quotes.")
                error_details = {
                    'location': 'headers',
                    'description': message
                }
                raise_invalid(self.request, **error_details)
        else:
            # In case _raise_304_if_not_modified() did not raise.
            return

        if record:
            current_timestamp = record[self.model.modified_field]
        else:
            current_timestamp = self.model.timestamp()

        if current_timestamp > modified_since:
            error_msg = 'Resource was modified meanwhile'
            details = {'existing': record} if record else {}
            response = http_error(HTTPPreconditionFailed(),
                                  errno=ERRORS.MODIFIED_MEANWHILE,
                                  message=error_msg,
                                  details=details)
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_conflict(self, exception):
        """Helper to raise conflict responses.

        :param exception: the original unicity error
        :type exception: :class:`kinto.core.storage.exceptions.UnicityError`
        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPConflict`
        """
        field = exception.field
        record_id = exception.record[self.model.id_field]
        message = 'Conflict of field %s on record %s' % (field, record_id)
        details = {
            "field": field,
            "existing": exception.record,
        }
        response = http_error(HTTPConflict(),
                              errno=ERRORS.CONSTRAINT_VIOLATED,
                              message=message,
                              details=details)
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
        fields = self.request.GET.get('_fields', None)
        if fields:
            fields = fields.split(',')
            root_fields = [f.split('.')[0] for f in fields]
            known_fields = self._get_known_fields()
            invalid_fields = set(root_fields) - set(known_fields)
            preserve_unknown = self.mapping.get_option('preserve_unknown')
            if not preserve_unknown and invalid_fields:
                error_msg = "Fields %s do not exist" % ','.join(invalid_fields)
                error_details = {
                    'name': "Invalid _fields parameter",
                    'description': error_msg
                }
                raise_invalid(self.request, **error_details)

            # Since id and last_modified are part of the synchronisation
            # protocol, force their presence in payloads.
            fields = fields + [self.model.id_field, self.model.modified_field]

        return fields

    def _extract_limit(self):
        """Extract limit value from QueryString parameters."""
        paginate_by = self.request.registry.settings['paginate_by']
        limit = self.request.GET.get('_limit', paginate_by)
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                error_details = {
                    'location': 'querystring',
                    'description': "_limit should be an integer"
                }
                raise_invalid(self.request, **error_details)

        # If limit is higher than paginate_by setting, ignore it.
        if limit and paginate_by:
            limit = min(limit, paginate_by)

        return limit

    def _extract_filters(self, queryparams=None):
        """Extracts filters from QueryString parameters."""
        if not queryparams:
            queryparams = self.request.GET

        filters = []

        for param, paramvalue in queryparams.items():
            param = param.strip()

            error_details = {
                'name': param,
                'location': 'querystring',
                'description': 'Invalid value for %s' % param
            }

            # Ignore specific fields
            if param.startswith('_') and param not in ('_since',
                                                       '_to',
                                                       '_before'):
                continue

            # Handle the _since specific filter.
            if param in ('_since', '_to', '_before'):
                value = native_value(paramvalue.strip('"'))

                if not isinstance(value, six.integer_types):
                    raise_invalid(self.request, **error_details)

                if param == '_since':
                    operator = COMPARISON.GT
                else:
                    if param == '_to':
                        message = ('_to is now deprecated, '
                                   'you should use _before instead')
                        url = ('http://kinto.rtfd.org/en/2.4.0/api/resource'
                               '.html#list-of-available-url-parameters')
                        send_alert(self.request, message, url)
                    operator = COMPARISON.LT
                filters.append(
                    Filter(self.model.modified_field, value, operator)
                )
                continue

            m = re.match(r'^(min|max|not|lt|gt|in|exclude)_(\w+)$', param)
            if m:
                keyword, field = m.groups()
                operator = getattr(COMPARISON, keyword.upper())
            else:
                operator, field = COMPARISON.EQ, param

            if not self.is_known_field(field):
                error_msg = "Unknown filter field '{0}'".format(param)
                error_details['description'] = error_msg
                raise_invalid(self.request, **error_details)

            value = native_value(paramvalue)
            if operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                value = set([native_value(v) for v in paramvalue.split(',')])

                all_integers = all([isinstance(v, six.integer_types)
                                    for v in value])
                all_strings = all([isinstance(v, six.text_type)
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
        specified = self.request.GET.get('_sort', '').split(',')
        sorting = []
        modified_field_used = self.model.modified_field in specified
        for field in specified:
            field = field.strip()
            m = re.match(r'^([\-+]?)(\w+)$', field)
            if m:
                order, field = m.groups()

                if not self.is_known_field(field):
                    error_details = {
                        'location': 'querystring',
                        'description': "Unknown sort field '{0}'".format(field)
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
        queryparams = self.request.GET
        token = queryparams.get('_token', None)
        filters = []
        offset = 0
        if token:
            try:
                tokeninfo = json.loads(decode64(token))
                if not isinstance(tokeninfo, dict):
                    raise ValueError()
                last_record = tokeninfo['last_record']
                offset = tokeninfo['offset']
            except (ValueError, KeyError, TypeError):
                error_msg = '_token has invalid content'
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

        params = self.request.GET.copy()
        params['_limit'] = limit
        params['_token'] = token

        service = self.request.current_service
        next_page_url = self.request.route_url(service.name, _query=params,
                                               **self.request.matchdict)
        return next_page_url

    def _build_pagination_token(self, sorting, last_record, offset):
        """Build a pagination token.

        It is a base64 JSON object with the sorting fields values of
        the last_record.

        """
        token = {
            'last_record': {},
            'offset': offset
        }

        for field, _ in sorting:
            token['last_record'][field] = last_record[field]

        return encode64(json.dumps(token))


@six.add_metaclass(DeprecatedMeta)
class BaseResource(UserResource):
    __deprecation_warning__ = ('BaseResource is deprecated. '
                               'Use UserResource instead.')


class ShareableResource(UserResource):
    """Shareable resources allow to set permissions on records, in order to
    share their access or protect their modification.
    """
    default_model = ShareableModel
    default_viewset = ShareableViewSet
    permissions = ('read', 'write')
    """List of allowed permissions names."""

    def __init__(self, *args, **kwargs):
        super(ShareableResource, self).__init__(*args, **kwargs)
        # In base resource, PATCH only hit storage if no data has changed.
        # Here, we force update because we add the current principal to
        # the ``write`` ACE.
        self.force_patch_update = True

        # Required by the ShareableModel class.
        self.model.permission = self.request.registry.permission
        self.model.current_principal = self.request.prefixed_userid
        if self.context:
            self.model.get_permission_object_id = functools.partial(
                self.context.get_permission_object_id,
                self.request)

    def get_parent_id(self, request):
        """Unlike :class:`BaseResource`, records are not isolated by user.

        See https://github.com/mozilla-services/cliquet/issues/549

        :returns: A constant empty value.
        """
        return ''

    def _extract_filters(self, queryparams=None):
        """Override default filters extraction from QueryString to allow
        partial collection of records.

        XXX: find more elegant approach to add custom filters.
        """
        filters = super(ShareableResource, self)._extract_filters(queryparams)

        ids = self.context.shared_ids
        if ids:
            filter_by_id = Filter(self.model.id_field, ids, COMPARISON.IN)
            filters.insert(0, filter_by_id)

        return filters

    def _raise_412_if_modified(self, record=None):
        """Do not provide the permissions among the record fields.
        Ref: https://github.com/Kinto/kinto/issues/224
        """
        if record:
            record = record.copy()
            record.pop(self.model.permissions_field, None)
        return super(ShareableResource, self)._raise_412_if_modified(record)

    def process_record(self, new, old=None):
        """Read permissions from request body, and in the case of ``PUT`` every
        existing ACE is removed (using empty list).
        """
        new = super(ShareableResource, self).process_record(new, old)
        permissions = self.request.validated.get('permissions', {})

        annotated = new.copy()

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

        In the protocol, it was decided that ``permissions`` would reside
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

        data = super(ShareableResource, self).postprocess(result, action, old)
        body.update(data)
        return body


@six.add_metaclass(DeprecatedMeta)
class ProtectedResource(ShareableResource):
    __deprecation_warning__ = ('ProtectedResource is deprecated. '
                               'Use ShareableResource instead.')
