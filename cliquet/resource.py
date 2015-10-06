import re
import functools

import colander
import venusian
import six
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound, HTTPConflict)

from cliquet import logger
from cliquet import Service
from cliquet.collection import Collection, ProtectedCollection
from cliquet.viewset import ViewSet, ProtectedViewSet
from cliquet.errors import http_error, raise_invalid, send_alert, ERRORS
from cliquet.schema import ResourceSchema
from cliquet.storage import exceptions as storage_exceptions, Filter, Sort
from cliquet.utils import (
    COMPARISON, classname, native_value, decode64, encode64, json,
    current_service, encode_header, decode_header
)


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
        services = [register_service('collection', config.registry.settings),
                    register_service('record', config.registry.settings)]
        for service in services:
            config.add_cornice_service(service)

    info = venusian.attach(resource_cls, callback, category='pyramid',
                           depth=depth)
    return callback


class BaseResource(object):
    """Base resource class providing every endpoint."""

    default_viewset = ViewSet
    """Default :class:`cliquet.viewset.ViewSet` class to use when the resource
    is registered."""

    default_collection = Collection
    """Default :class:`cliquet.collection.Collection` class to use for
    interacting the :module:`cliquet.storage` and :module:`cliquet.permission`
    backends."""

    mapping = ResourceSchema()
    """Schema to validate records."""

    def __init__(self, request, context=None):
        # Collections are isolated by user.
        parent_id = self.get_parent_id(request)

        # Authentication to storage is transmitted as is (cf. cloud_storage).
        auth = request.headers.get('Authorization')

        self.collection = self.default_collection(
            storage=request.registry.storage,
            id_generator=request.registry.id_generator,
            collection_id=classname(self),
            parent_id=parent_id,
            auth=auth)

        self.request = request
        self.context = context
        self.timestamp = self.collection.timestamp()
        self.record_id = self.request.matchdict.get('id')
        self.force_patch_update = False

        # Log resource context.
        logger.bind(collection_id=self.collection.collection_id,
                    collection_timestamp=self.timestamp)

    def get_parent_id(self, request):
        """Return the parent_id of the resource with regards to the current
        request.

        :param request:
            The request used to create the resource.

        :rtype: str

        """
        return getattr(request, 'prefixed_userid', None)

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
            headers['Next-Page'] = encode_header(next_page)

        # Bind metric about response size.
        logger.bind(nb_records=len(records), limit=limit)
        headers['Total-Records'] = encode_header('%s' % total_records)

        return self.postprocess(records)

    def collection_post(self):
        """Collection ``POST`` endpoint: create a record.

        If the new record conflicts against a unique field constraint, the
        posted record is ignored, and the existing record is returned, with
        a ``200`` status.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and collection modified
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
        except (KeyError, ValueError):
            pass

        new_record = self.process_record(new_record)

        try:
            unique_fields = self.mapping.get_option('unique_fields')
            record = self.collection.create_record(new_record,
                                                   unique_fields=unique_fields)
            self.request.response.status_code = 201
        except storage_exceptions.UnicityError as e:
            record = e.record

        return self.postprocess(record)

    def collection_delete(self):
        """Collection ``DELETE`` endpoint: delete multiple records.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Match`` header is provided and collection modified
            in the iterim.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters are invalid.
        """
        self._raise_412_if_modified()

        filters = self._extract_filters()
        deleted = self.collection.delete_records(filters=filters)

        return self.postprocess(deleted)

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
        timestamp = record[self.collection.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)
        self._add_cache_header(self.request.response)
        self._raise_304_if_not_modified(record)
        self._raise_412_if_modified(record)

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

        new_record = self.request.validated['data']

        record_id = new_record.setdefault(id_field, self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(new_record, old=existing)

        try:
            unique = self.mapping.get_option('unique_fields')
            if existing:
                record = self.collection.update_record(new_record,
                                                       unique_fields=unique)
            else:
                record = self.collection.create_record(new_record,
                                                       unique_fields=unique)
                self.request.response.status_code = 201

        except storage_exceptions.UnicityError as e:
            self._raise_conflict(e)

        timestamp = record[self.collection.modified_field]
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(record)

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
            :meth:`cliquet.resource.BaseResource.apply_changes` or
            :meth:`cliquet.resource.BaseResource.process_record`.
        """
        self._raise_400_if_invalid_id(self.record_id)
        old_record = self._get_record_or_404(self.record_id)
        self._raise_412_if_modified(old_record)

        changes = self.request.json.get('data', {})  # May patch only perms.

        updated = self.apply_changes(old_record, changes=changes)

        record_id = updated.setdefault(self.collection.id_field,
                                       self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(updated, old=old_record)

        changed_fields = [k for k in changes.keys()
                          if old_record.get(k) != new_record.get(k)]

        # Save in storage if necessary.
        if changed_fields or self.force_patch_update:
            try:
                unique_fields = self.mapping.get_option('unique_fields')
                new_record = self.collection.update_record(
                    updated,
                    unique_fields=unique_fields)
            except storage_exceptions.UnicityError as e:
                self._raise_conflict(e)
        else:
            # Behave as if storage would have added `id` and `last_modified`.
            for extra_field in [self.collection.modified_field,
                                self.collection.id_field]:
                new_record[extra_field] = old_record[extra_field]

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

        timestamp = new_record.get(self.collection.modified_field,
                                   old_record[self.collection.modified_field])
        self._add_timestamp_header(self.request.response, timestamp=timestamp)

        return self.postprocess(data)

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

        deleted = self.collection.delete_record(record)

        return self.postprocess(deleted)

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

    def postprocess(self, result):
        body = {
            'data': result
        }
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
        response.headers['ETag'] = encode_header('"%s"' % timestamp)

    def _add_cache_header(self, response):
        """Add Cache-Control and Expire headers, based a on a setting for the
        current resource.
        """
        resource_name = self.context.resource_name if self.context else ''
        setting_key = '%s_cache_expires_seconds' % resource_name
        collection_expires = self.request.registry.settings.get(setting_key)
        if collection_expires is not None:
            response.cache_expires(seconds=int(collection_expires))

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

        if_none_match = decode_header(if_none_match)

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

        if_match = decode_header(if_match) if if_match else None

        if if_none_match and decode_header(if_none_match) == '*':
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
        else:
            # In case _raise_304_if_not_modified() did not raise.
            return

        if record:
            current_timestamp = record[self.collection.modified_field]
        else:
            current_timestamp = self.collection.timestamp()

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
            value = native_value(paramvalue)

            # Ignore specific fields
            if param.startswith('_') and param not in ('_since',
                                                       '_to',
                                                       '_before'):
                continue

            # Handle the _since specific filter.
            if param in ('_since', '_to', '_before'):
                if not isinstance(value, six.integer_types):
                    error_details = {
                        'name': param,
                        'location': 'querystring',
                        'description': 'Invalid value for %s' % param
                    }
                    raise_invalid(self.request, **error_details)

                if param == '_since':
                    operator = COMPARISON.GT
                else:
                    if param == '_to':
                        message = ('_to is now deprecated, '
                                   'you should use _before instead')
                        url = ('http://cliquet.rtfd.org/en/2.4.0/api/resource'
                               '.html#list-of-available-url-parameters')
                        send_alert(self.request, message, url)
                    operator = COMPARISON.LT
                filters.append(
                    Filter(self.collection.modified_field, value, operator)
                )
                continue

            m = re.match(r'^(min|max|not|lt|gt|in|exclude)_(\w+)$', param)
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

            if operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                value = set([native_value(v) for v in paramvalue.split(',')])

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
    """Protected resources allow to set permissions on records, in order to
    share their access or protect their modification.
    """
    default_collection = ProtectedCollection
    default_viewset = ProtectedViewSet
    permissions = ('read', 'write')
    """List of allowed permissions names."""

    def __init__(self, *args, **kwargs):
        super(ProtectedResource, self).__init__(*args, **kwargs)
        # In base resource, PATCH only hit storage if no data has changed.
        # Here, we force update because we add the current principal to
        # the ``write`` ACE.
        self.force_patch_update = True

        # Required by the ProtectedCollection class.
        self.collection.permission = self.request.registry.permission
        self.collection.current_principal = self.request.prefixed_userid
        if self.context:
            self.collection.get_permission_object_id = functools.partial(
                self.context.get_permission_object_id,
                self.request)

    def _extract_filters(self, queryparams=None):
        """Override default filters extraction from QueryString to allow
        partial collection of records.

        XXX: find more elegant approach to add custom filters.
        """
        filters = super(ProtectedResource, self)._extract_filters(queryparams)

        ids = self.context.shared_ids
        if ids:
            filter_by_id = Filter(self.collection.id_field, ids, COMPARISON.IN)
            filters.insert(0, filter_by_id)

        return filters

    def process_record(self, new, old=None):
        """Read permissions from request body, and in the case of ``PUT`` every
        existing ACE is removed (using empty list).
        """
        permissions = self.request.validated.get('permissions', {})

        if permissions:
            is_put = (self.request.method.lower() == 'put')
            if is_put:
                # Remove every existing ACEs using empty lists.
                for perm in self.permissions:
                    permissions.setdefault(perm, [])
            new[self.collection.permissions_field] = permissions

        return new

    def postprocess(self, result):
        """Add ``permissions`` attribute in response body.

        In the protocol, it was decided that ``permissions`` would reside
        outside the ``data`` attribute.
        """
        result = super(ProtectedResource, self).postprocess(result)
        if not isinstance(result['data'], list):
            perms = result['data'].pop(self.collection.permissions_field, None)
            if perms is not None:
                result['permissions'] = {k: list(p) for k, p in perms.items()}
        return result
