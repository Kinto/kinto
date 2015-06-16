import re
import functools

import colander
import venusian
import six
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound, HTTPConflict)

from cliquet import authorization
from cliquet import logger
from cliquet import Service
from cliquet.collection import Collection
from cliquet.errors import (http_error, raise_invalid, ERRORS,
                            json_error_handler)
from cliquet.schema import ResourceSchema, PermissionsSchema
from cliquet.storage import exceptions as storage_exceptions, Filter, Sort
from cliquet.utils import (
    COMPARISON, classname, native_value, decode64, encode64, json,
    current_service
)


class ViewSet(object):
    """The default ViewSet object.

    A viewset contains all the information needed to register
    any resource in the Cornice registry.

    It provides the same features as ``cornice.resource()``, except
    that it is much more flexible and extensible.
    """
    service_name = "{resource_name}-{endpoint_type}"
    collection_path = "/{resource_name}s"
    record_path = "/{resource_name}s/{{id}}"

    collection_methods = ('GET', 'POST', 'DELETE')
    record_methods = ('GET', 'PUT', 'PATCH', 'DELETE')
    validate_schema_for = ('POST', 'PUT')

    readonly_methods = ('GET',)

    service_arguments = {
        'description': 'Collection of {resource_name}',
        'cors_origins': ('*',),
        'error_handler': json_error_handler
    }

    default_arguments = {}

    default_collection_arguments = {}
    collection_get_arguments = {
        'cors_headers': ('Next-Page', 'Total-Records', 'Last-Modified', 'ETag')
    }

    default_record_arguments = {}
    record_get_arguments = {
        'cors_headers': ('Last-Modified', 'ETag')
    }

    def __init__(self, **kwargs):
        self.update(**kwargs)
        self.record_arguments = functools.partial(
            self.get_view_args, 'record')
        self.collection_arguments = functools.partial(
            self.get_view_args, 'collection')

    def update(self, **kwargs):
        """Update viewset attributes with provided values."""
        self.__dict__.update(**kwargs)

    def get_view_args(self, endpoint_type, resource, method):
        """Return the Pyramid/Cornice view arguments for the given endpoint
        type and method.

        :param str endpoint_type: either "collection" or "record".
        :param resource: the resource object.
        :param str method: the HTTP method.
        """
        args = self.default_arguments.copy()
        default_arguments = getattr(self,
                                    'default_%s_arguments' % endpoint_type)
        args.update(**default_arguments)

        by_method = '%s_%s_arguments' % (endpoint_type, method.lower())
        method_args = getattr(self, by_method, {})
        args.update(**method_args)

        args['schema'] = self.get_record_schema(resource, method)

        return args

    def get_record_schema(self, resource, method):
        """Return the Cornice schema for the given method.
        """
        if method.lower() not in map(str.lower, self.validate_schema_for):
            # Simply validate that posted body is a mapping.
            return colander.MappingSchema(unknown='preserve')

        # XXX: https://github.com/mozilla-services/cliquet/issues/322
        resource_permissions = getattr(resource, 'permissions', tuple())

        class RecordPayload(colander.MappingSchema):
            data = resource.mapping
            permissions = PermissionsSchema(
                missing=colander.drop,
                permissions=resource_permissions)

            def schema_type(self, **kw):
                return colander.Mapping(unknown='raise')

        return RecordPayload()

    def get_view(self, endpoint_type, method):
        """Return the view method name located on the resource object, for the
        given type and method.

        * For collections, this will be "collection_{method|lower}
        * For records, this will be "{method|lower}.
        """
        if endpoint_type == 'record':
            return method.lower()
        return '%s_%s' % (endpoint_type, method.lower())

    def get_name(self, resource):
        """Returns the name of the resource.
        """
        if 'name' in self.__dict__:
            name = self.__dict__['name']
        elif hasattr(resource, 'name') and not callable(resource.name):
            name = resource.name
        else:
            name = resource.__name__.lower()

        return name

    def get_service_name(self, endpoint_type, resource):
        """Returns the name of the service, depending a given type and
        resource.
        """
        return self.service_name.format(
            resource_name=self.get_name(resource),
            endpoint_type=endpoint_type)

    def get_service_arguments(self):
        service_arguments = {}
        if hasattr(self, 'factory'):
            service_arguments['factory'] = self.factory
        service_arguments.update(self.service_arguments)
        return service_arguments

    def is_endpoint_enabled(self, endpoint_type, resource_name, method,
                            settings):
        """Returns if the given endpoint is enabled or not.

        Uses the settings to tell so.
        """
        setting_enabled = 'cliquet.%s_%s_%s_enabled' % (
            endpoint_type, resource_name, method.lower())
        return settings.get(setting_enabled, True)


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


def register_resource(resource, settings=None, viewset=None, depth=1,
                      **kwargs):
    """Register a resource in the cornice registry.

    :param resource:
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
        viewset = ViewSet(**kwargs)
    else:
        viewset.update(**kwargs)

    resource_name = viewset.get_name(resource)

    path_formatters = {
        'resource_name': resource_name
    }

    def register_service(endpoint_type, settings):
        """Registers a service in cornice, for the given type."""
        path_pattern = getattr(viewset, '%s_path' % endpoint_type)
        path = path_pattern.format(**path_formatters)

        name = viewset.get_service_name(endpoint_type, resource)

        service = Service(name, path, depth=depth,
                          **viewset.get_service_arguments())

        # Attach viewset and resource to the service for later reference.
        service.viewset = viewset
        service.resource = resource
        service.collection_path = viewset.collection_path.format(
            **path_formatters)
        service.record_path = viewset.record_path.format(**path_formatters)

        methods = getattr(viewset, '%s_methods' % endpoint_type)
        for method in methods:
            if not viewset.is_endpoint_enabled(
                    endpoint_type, resource_name, method.lower(), settings):
                continue

            argument_getter = getattr(viewset, '%s_arguments' % endpoint_type)
            view_args = argument_getter(resource, method)

            view = viewset.get_view(endpoint_type, method.lower())
            service.add_view(method, view, klass=resource, **view_args)

        return service

    def callback(context, name, ob):
        # get the callbacks registred by the inner services
        # and call them from here when the @resource classes are being
        # scanned by venusian.
        config = context.config.with_package(info.module)
        services = [register_service('collection', config.registry.settings),
                    register_service('record', config.registry.settings)]
        for service in services:
            config.add_cornice_service(service)

    info = venusian.attach(resource, callback, category='pyramid',
                           depth=depth)
    return callback


class BaseResource(object):
    """Base resource class providing every endpoint."""

    mapping = ResourceSchema()
    """Schema to validate records."""

    def __init__(self, request, context=None):

        # Collections are isolated by user.
        parent_id = request.authenticated_userid
        # Authentication to storage is transmitted as is (cf. cloud_storage).
        auth = request.headers.get('Authorization')

        self.collection = Collection(
            storage=request.registry.storage,
            id_generator=request.registry.id_generator,
            collection_id=classname(self),
            parent_id=parent_id,
            auth=auth)

        self.request = request
        self.context = context
        self.timestamp = self.collection.timestamp()
        self.record_id = self.request.matchdict.get('id')

        # Log resource context.
        logger.bind(collection_id=self.collection.collection_id,
                    collection_timestamp=self.timestamp)

    def is_known_field(self, field):
        """Return ``True`` if `field` is defined in the resource mapping.

        :param str field: Field name
        :rtype: bool

        """
        known_fields = [c.name for c in self.mapping.children] + \
                       [self.collection.id_field,
                        self.collection.modified_field,
                        self.collection.deleted_field]
        return field in known_fields

    #
    # End-points
    #

    def collection_get(self):
        """Collection ``GET`` endpoint: retrieve multiple records.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified` if
            ``If-Modified-Since`` header is provided and collection not
            modified in the interim.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and collection modified
            in the iterim.
        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters or sorting are invalid.
        """
        self._add_timestamp_header(self.request.response)
        self._raise_304_if_not_modified()
        self._raise_412_if_modified()

        headers = self.request.response.headers
        filters = self._extract_filters()
        sorting = self._extract_sorting()
        limit = self._extract_limit()
        filter_fields = [f.field for f in filters]
        include_deleted = self.collection.modified_field in filter_fields

        pagination_rules = self._extract_pagination_rules_from_token(
            limit, sorting)

        records, total_records = self.collection.get_records(
            filters=filters,
            sorting=sorting,
            limit=limit,
            pagination_rules=pagination_rules,
            include_deleted=include_deleted)

        next_page = None
        if limit and len(records) == limit and total_records > limit:
            next_page = self._next_page_url(sorting, limit, records[-1])
            headers['Next-Page'] = next_page

        # Bind metric about response size.
        logger.bind(nb_records=len(records), limit=limit)
        headers['Total-Records'] = ('%s' % total_records)

        body = {
            'data': records,
        }
        return body

    def collection_post(self):
        """Collection ``POST`` endpoint: create a record.

        If the new record conflicts against a unique field constraint, the
        posted record is ignored, and the existing record is returned, with
        a ``200`` status.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and collection modified
            in the iterim.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`cliquet.resource.BaseResource.process_record`
        """
        self._raise_412_if_modified()

        new_record = self.request.validated['data']

        # Since ``id`` does not belong to schema, it can only be found in body.
        try:
            id_field = self.collection.id_field
            new_record[id_field] = _id = self.request.json['data'][id_field]
            self._raise_400_if_invalid_id(_id)
        except KeyError:
            pass

        new_record = self.process_record(new_record)

        try:
            unique_fields = self.mapping.get_option('unique_fields')
            record = self.collection.create_record(new_record,
                                                   unique_fields=unique_fields)
            self.request.response.status_code = 201
        except storage_exceptions.UnicityError as e:
            record = e.record

        body = {
            'data': record,
        }
        return body

    def collection_delete(self):
        """Collection ``DELETE`` endpoint: delete multiple records.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and collection modified
            in the iterim.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters are invalid.
        """
        self._raise_412_if_modified()

        filters = self._extract_filters()
        deleted = self.collection.delete_records(filters=filters)

        body = {
            'data': deleted,
        }
        return body

    def get(self):
        """Record ``GET`` endpoint: retrieve a record.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotModified` if
            ``If-Modified-Since`` header is provided and record not
            modified in the interim.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and record modified
            in the iterim.
        """
        self._raise_400_if_invalid_id(self.record_id)
        self._add_timestamp_header(self.request.response)
        record = self._get_record_or_404(self.record_id)
        self._raise_304_if_not_modified(record)
        self._raise_412_if_modified(record)

        body = {
            'data': record,
        }
        return body

    def put(self):
        """Record ``PUT`` endpoint: create or replace the provided record and
        return it.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and record modified
            in the iterim.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`cliquet.resource.BaseResource.process_record`.
        """
        self._raise_400_if_invalid_id(self.record_id)
        id_field = self.collection.id_field
        existing = None
        try:
            existing = self._get_record_or_404(self.record_id)
        except HTTPNotFound:
            # Look if this record used to exist (for preconditions check).
            deleted = Filter(id_field, self.record_id, COMPARISON.EQ)
            result, _ = self.collection.get_records(filters=[deleted],
                                                    include_deleted=True)
            if len(result) > 0:
                existing = result[0]
        finally:
            if existing:
                self._raise_412_if_modified(existing)
            else:
                self.request.response.status_code = 201

        new_record = self.request.validated['data']

        record_id = new_record.setdefault(id_field, self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(new_record, old=existing)

        try:
            unique_fields = self.mapping.get_option('unique_fields')
            record = self.collection.update_record(new_record,
                                                   unique_fields=unique_fields)
        except storage_exceptions.UnicityError as e:
            self._raise_conflict(e)

        body = {
            'data': record,
        }
        return body

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
            ``If-Unmodified-Since`` header is provided and record modified
            in the iterim.

        .. seealso::
            Add custom behaviour by overriding
            :meth:`cliquet.resource.BaseResource.apply_changes` or
            :meth:`cliquet.resource.BaseResource.process_record`.
        """
        self._raise_400_if_invalid_id(self.record_id)
        old_record = self._get_record_or_404(self.record_id)
        self._raise_412_if_modified(old_record)

        # Empty body for patch is invalid.
        if not self.request.body:
            error_details = {
                'description': 'Empty body'
            }
            raise_invalid(self.request, **error_details)

        changes = self.request.json.get('data', {})  # May patch only perms.

        updated = self.apply_changes(old_record, changes=changes)

        record_id = updated.setdefault(self.collection.id_field,
                                       self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(updated, old=old_record)

        changed_fields = [k for k in changes.keys()
                          if old_record.get(k) != new_record.get(k)]

        # Save in storage if necessary.
        if changed_fields:
            try:
                unique_fields = self.mapping.get_option('unique_fields')
                new_record = self.collection.update_record(
                    updated,
                    unique_fields=unique_fields)
            except storage_exceptions.UnicityError as e:
                self._raise_conflict(e)

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

        body = {
            'data': data,
        }
        return body

    def delete(self):
        """Record ``DELETE`` endpoint: delete a record and return it.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and record modified
            in the iterim.
        """
        self._raise_400_if_invalid_id(self.record_id)
        record = self._get_record_or_404(self.record_id)
        self._raise_412_if_modified(record)

        deleted = self.collection.delete_record(record)

        body = {
            'data': deleted,
        }
        return body

    #
    # Data processing
    #

    def process_record(self, new, old=None):
        """Hook for processing records before they reach storage, to introduce
        specific logics on fields for example.

        .. code-block:: python

            def process_record(self, new, old=None):
                version = old['version'] if old else 0
                new['version'] = version + 1
                return new

        Or add extra validation based on request:

        .. code-block:: python

            from cliquet.errors import raise_invalid

            def process_record(self, new, old=None):
                if new['browser'] not in request.headers['User-Agent']:
                    raise_invalid(self.request, name='browser', error='Wrong')
                return new

        :param dict new: the validated record to be created or updated.
        :param dict old: the old record to be updated,
            ``None`` for creation endpoints.

        :returns: the processed record.
        :rtype: dict
        """
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

    #
    # Internals
    #

    def _get_record_or_404(self, record_id):
        """Retrieve record from storage and raise ``404 Not found`` if missing.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound` if
            the record is not found.
        """
        try:
            return self.collection.get_record(record_id)
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
        response.headers['ETag'] = ('"%s"' % timestamp).encode('utf-8')

    def _raise_400_if_invalid_id(self, record_id):
        """Raise 400 if specified record id does not match the format excepted
        by storage backends.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        if not self.collection.id_generator.match(six.text_type(record_id)):
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

        if_none_match = if_none_match.decode('utf-8')

        try:
            assert if_none_match[0] == if_none_match[-1] == '"'
            modified_since = int(if_none_match[1:-1])
        except (IndexError, AssertionError, ValueError):
            if if_none_match != '*':
                error_details = {
                    'location': 'headers',
                    'description': "Invalid value for If-None-Match"
                }
                raise_invalid(self.request, **error_details)

        if record:
            current_timestamp = record[self.collection.modified_field]
        else:
            current_timestamp = self.collection.timestamp()

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

        if_match = if_match.decode('utf-8') if if_match else None

        if if_none_match and if_none_match.decode('utf-8') == '*':
            modified_since = -1  # Always raise.
        elif if_match:
            try:
                assert if_match[0] == if_match[-1] == '"'
                modified_since = int(if_match[1:-1])
            except (IndexError, AssertionError, ValueError):
                error_details = {
                    'location': 'headers',
                    'description': "Invalid value for If-Match"
                }
                raise_invalid(self.request, **error_details)

        if record:
            current_timestamp = record[self.collection.modified_field]
        else:
            current_timestamp = self.collection.timestamp()

        if current_timestamp > modified_since:
            error_msg = 'Resource was modified meanwhile'
            response = http_error(HTTPPreconditionFailed(),
                                  errno=ERRORS.MODIFIED_MEANWHILE,
                                  message=error_msg)
            self._add_timestamp_header(response, timestamp=current_timestamp)
            raise response

    def _raise_conflict(self, exception):
        """Helper to raise conflict responses.

        :param exception: the original unicity error
        :type exception: :class:`cliquet.storage.exceptions.UnicityError`
        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPConflict`
        """
        field = exception.field
        record_id = exception.record[self.collection.id_field]
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
                'name': self.collection.id_field,
                'description': error_msg
            }
            raise_invalid(self.request, **error_details)

    def _extract_limit(self):
        """Extract limit value from QueryString parameters."""
        paginate_by = self.request.registry.settings['cliquet.paginate_by']
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

        for param, value in queryparams.items():
            param = param.strip()
            value = native_value(value)

            # Ignore specific fields
            if param.startswith('_') and param not in ('_since', '_to'):
                continue

            # Handle the _since specific filter.
            if param in ('_since', '_to'):
                if not isinstance(value, six.integer_types):
                    error_details = {
                        'name': param,
                        'location': 'querystring',
                        'description': 'Invalid value for _since'
                    }
                    raise_invalid(self.request, **error_details)

                if param == '_since':
                    operator = COMPARISON.GT
                else:
                    operator = COMPARISON.LT
                filters.append(
                    Filter(self.collection.modified_field, value, operator)
                )
                continue

            m = re.match(r'^(min|max|not|lt|gt)_(\w+)$', param)
            if m:
                keyword, field = m.groups()
                operator = getattr(COMPARISON, keyword.upper())
            else:
                operator, field = COMPARISON.EQ, param

            if not self.is_known_field(field):
                error_details = {
                    'location': 'querystring',
                    'description': "Unknown filter field '{0}'".format(param)
                }
                raise_invalid(self.request, **error_details)

            filters.append(Filter(field, value, operator))

        return filters

    def _extract_sorting(self):
        """Extracts filters from QueryString parameters."""
        specified = self.request.GET.get('_sort', '').split(',')
        limit = '_limit' in self.request.GET
        sorting = []
        modified_field_used = self.collection.modified_field in specified
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

        if not modified_field_used and limit:
            # Add a sort by the ``modified_field`` in descending order
            # useful for pagination
            sorting.append(Sort(self.collection.modified_field, -1))
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
        if token:
            try:
                last_record = json.loads(decode64(token))
                assert isinstance(last_record, dict)
            except (ValueError, TypeError, AssertionError):
                error_msg = '_token has invalid content'
                error_details = {
                    'location': 'querystring',
                    'description': error_msg
                }
                raise_invalid(self.request, **error_details)

            filters = self._build_pagination_rules(sorting, last_record)
        return filters

    def _next_page_url(self, sorting, limit, last_record):
        """Build the Next-Page header from where we stopped."""
        token = self._build_pagination_token(sorting, last_record)

        params = self.request.GET.copy()
        params['_limit'] = limit
        params['_token'] = token

        service = current_service(self.request)
        next_page_url = self.request.route_url(service.name, _query=params,
                                               **self.request.matchdict)
        return next_page_url

    def _build_pagination_token(self, sorting, last_record):
        """Build a pagination token.

        It is a base64 JSON object with the sorting fields values of
        the last_record.

        """
        token = {}

        for field, _ in sorting:
            token[field] = last_record[field]

        return encode64(json.dumps(token))


class ProtectedResource(BaseResource):
    permissions = ('read', 'write')

    def _store_permissions(self, object_id, replace=False):
        """Go through the permissions from request body, and store them
        for the specified `object_id`.

        :param bool replace: If ``True`` any existing permission will be
            erased.
        :returns: the resulting mapping of permissions.
        """
        permissions = self.request.validated.get('permissions')

        add_write_perm = (self.request.method.lower() in ('put', 'post'))

        # Do nothing if not specified in request body.
        if not permissions:
            permissions = self._build_permissions(object_id)

        if add_write_perm:
            write_principals = permissions.setdefault('write', [])
            user_principal = self.request.authenticated_userid
            if user_principal not in write_principals:
                write_principals.insert(0, user_principal)

        if replace:
            # XXX: add replace method to permissions API.
            self._delete_permissions(object_id)

        registry = self.request.registry
        add_principal = registry.permission.add_principal_to_ace

        for permission, principals in permissions.items():
            for principal in principals:
                add_principal(object_id, permission, principal)

        return permissions

    def _delete_permissions(self, object_id):
        registry = self.request.registry
        del_principal = registry.permission.remove_principal_from_ace
        get_perm_principals = registry.permission.object_permission_principals

        for permission in self.permissions:
            existing = list(get_perm_principals(object_id, permission))
            for principal in existing:
                del_principal(object_id, permission, principal)

    def _build_permissions(self, object_id):
        """Fetch the stored permissions for the specified `object_id` and
        returns a mapping representing ACLs.
        """
        registry = self.request.registry
        get_perm_principals = registry.permission.object_permission_principals

        permissions = {}
        for perm in self.permissions:
            principals = get_perm_principals(object_id, perm)
            if principals:
                permissions[perm] = list(principals)
        return permissions

    def _record_uri_from_collection(self, record_id):
        # Since the current request is on a collection, the record URI must
        # be found out by inspecting the collection service and its sibling
        # record service.
        service = current_service(self.request)
        record_service = service.name.replace('-collection', '-record')
        matchdict = self.request.matchdict.copy()
        matchdict['id'] = record_id
        record_uri = self.request.route_path(record_service, **matchdict)
        return record_uri

    def collection_post(self):
        """Override the collection POST endpoint to store the permissions
        specified for the newly created record.
        """
        result = super(ProtectedResource, self).collection_post()

        record_id = result['data'][self.collection.id_field]
        record_uri = self._record_uri_from_collection(record_id)

        object_id = authorization.get_object_id(record_uri)
        result['permissions'] = self._store_permissions(object_id=object_id)
        return result

    def collection_delete(self):
        """Override the collection DELETE endpoint to clear the permissions
        of the delete records.
        """
        result = super(ProtectedResource, self).collection_delete()

        for record in result['data']:
            record_id = record[self.collection.id_field]
            record_uri = self._record_uri_from_collection(record_id)

            # XXX: inefficient within loop.
            object_id = authorization.get_object_id(record_uri)
            self._delete_permissions(object_id)

        return result

    def get(self):
        result = super(ProtectedResource, self).get()

        object_id = authorization.get_object_id(self.request.path)
        result['permissions'] = self._build_permissions(object_id=object_id)
        return result

    def put(self):
        result = super(ProtectedResource, self).put()

        object_id = authorization.get_object_id(self.request.path)
        self._store_permissions(object_id=object_id, replace=True)
        result['permissions'] = self._build_permissions(object_id=object_id)
        return result

    def patch(self):
        result = super(ProtectedResource, self).patch()

        object_id = authorization.get_object_id(self.request.path)
        self._store_permissions(object_id=object_id)
        result['permissions'] = self._build_permissions(object_id=object_id)
        return result

    def delete(self):
        result = super(ProtectedResource, self).delete()

        object_id = authorization.get_object_id(self.request.path)
        self._delete_permissions(object_id=object_id)
        return result
