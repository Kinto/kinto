import re

import colander
from cornice import resource
from cornice.schemas import CorniceSchema
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPMethodNotAllowed,
                                    HTTPNotFound, HTTPConflict)
import six

from cliquet import logger
from cliquet.collection import Collection
from cliquet.errors import (http_error, raise_invalid, ERRORS,
                            json_error_handler)
from cliquet.schema import ResourceSchema
from cliquet.storage import exceptions as storage_exceptions, Filter, Sort
from cliquet.utils import (
    COMPARISON, classname, native_value, decode64, encode64, json,
    current_service
)


class ViewSet(object):
    collection_path = "/{resource_name}"
    record_path = "/{resource_name}/{{id}}"

    collection_methods = ('GET', 'POST', 'DELETE')
    record_methods = ('GET', 'PUT', 'PATCH', 'DELETE')
    readonly_methods = ('GET',)
    validate_schema_for = ('POST', 'PUT')

    default_arguments = {
        description: 'Collection of {resource_name}',
        cors_headers: ('Backoff', 'Retry-After', 'Alert'),
        cors_origins: ('*',),
        error_handler: json_error_handler
    }
    default_collection_arguments = {}
    default_collection_get_arguments = {
        cors_headers: (('Backoff', 'Retry-After', 'Alert') +
                       ('Next-Page', 'Total-Records', 'Last-Modified'))
    }
    default_record_arguments = {}
    default_record_get_arguments = {
        cors_headers: (('Backoff', 'Retry-After', 'Alert') +
                       ('Last-Modified',))
    }

    def __init__(self, **kwargs):
        self.update(**kwargs)

    def update(self, **kwargs):
        self.__dict__.update(**kwargs)

    def collection_arguments(self, resource, method):
        args = self.default_arguments().copy()
        args.update(**self.default_collection_arguments)

        by_method = 'default_collection_%s_arguments' % method.lower()
        method_args = getattr(self, by_method, {})
        args.update(**method_args)

        if method in self.readonly_methods:
            perm = '%s:readonly' % resource.name
        else:
            perm = '%s:readwrite' % resource.name
        args['permission'] = perm

        if method in self.validate_schema_for:
            args['schema'] = CorniceSchema.from_colander(resource.mapping,
                                                         bind_request=False)
        return args

    def record_arguments(self, resource, method):
        args = self.default_arguments().copy()
        args.update(**self.default_record_arguments)

        by_method = 'default_record_%s_arguments' % method.lower()
        method_args = getattr(self, by_method, {})
        args.update(**method_args)

        if method in self.readonly_methods:
            perm = '%s:readonly' % resource.name
        else:
            perm = '%s:readwrite' % resource.name
        args['permission'] = perm

        if method in self.validate_schema_for:
            args['schema'] = CorniceSchema.from_colander(resource.mapping,
                                                         bind_request=False)
        return args


def register(resource, viewset=None, **kwargs):
    # config.add_directive('register') ?
    settings = {}  # XXX:
    #cors_origins = tuple(aslist(settings['cliquet.cors_origins']))
    cors_origins = ('*',)

    if viewset is None:
        viewset = ViewSet(**kwargs)
    else:
        viewset.update(**kwargs)

    for method in viewset.collection_methods:
        setting_enabled = 'cliquet.collection_%s_%s_enabled' % (resource.name,
                                                                method.lower())
        if not settings.get(setting_enabled, True):
            continue

        view_args = viewset.collection_arguments(resource, method)
        view = getattr(resource, 'collection_%s' % method.lower())
        # register using Cornice
        service = Service()
        service.cors_origins = cors_origins
        service.definitions.append((method, view, view_args))

    for method in viewset.record_methods:
        setting_enabled = 'cliquet.%s_%s_enabled' % (resource.name,
                                                     method.lower())
        if not settings.get(setting_enabled, True):
            continue

        view_args = viewset.record_arguments(resource, method)
        view = getattr(resource, '%s' % method.lower())
        # register using Cornice
        service = Service()
        service.cors_origins = cors_origins
        service.definitions.append((method, view, view_args))


class BaseResource(object):
    """Base resource class providing every endpoint."""

    mapping = ResourceSchema()
    """Schema to validate records."""

    def __init__(self, request):
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
            'items': records,
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

        new_record = self.process_record(self.request.validated)

        try:
            unique_fields = self.mapping.get_option('unique_fields')
            record = self.collection.create_record(new_record,
                                                   unique_fields=unique_fields)
        except storage_exceptions.UnicityError as e:
            return e.record

        self.request.response.status_code = 201
        return record

    def collection_delete(self):
        """Collection ``DELETE`` endpoint: delete multiple records.

        Can be disabled via ``cliquet.delete_collection_enabled`` setting.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and collection modified
            in the iterim.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters are invalid.
        """
        settings = self.request.registry.settings
        enabled = settings['cliquet.delete_collection_enabled']
        if not enabled:
            # XXX: https://github.com/mozilla-services/cliquet/issues/46
            raise HTTPMethodNotAllowed()

        self._raise_412_if_modified()

        filters = self._extract_filters()
        deleted = self.collection.delete_records(filters=filters)

        body = {
            'items': deleted,
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
        return record

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

        new_record = self.request.validated

        record_id = new_record.setdefault(id_field, self.record_id)
        self._raise_400_if_id_mismatch(record_id, self.record_id)

        new_record = self.process_record(new_record, old=existing)

        try:
            unique_fields = self.mapping.get_option('unique_fields')
            record = self.collection.update_record(new_record,
                                                   unique_fields=unique_fields)
        except storage_exceptions.UnicityError as e:
            self._raise_conflict(e)

        return record

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

        changes = self.request.json

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
            return {k: new_record[k] for k in changed_fields}

        if body_behavior.lower() == 'diff':
            # Only fields that are different from those provided.
            return {k: new_record[k] for k in changed_fields
                    if changes.get(k) != new_record.get(k)}

        return new_record

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
        return deleted

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

    def _add_timestamp_header(self, response):
        """Add current timestamp in response headers, when request comes in.

        """
        timestamp = six.text_type(self.timestamp).encode('utf-8')
        response.headers['Last-Modified'] = timestamp

    def _raise_400_if_invalid_id(self, record_id):
        """Raise 400 if specified record id does not match the format excepted
        by storage backends.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
        """
        if not self.collection.id_generator.match(record_id):
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
        modified_since = self.request.headers.get('If-Modified-Since')

        if modified_since:
            modified_since = int(modified_since)

            if record:
                current_timestamp = record[self.collection.modified_field]
            else:
                current_timestamp = self.collection.timestamp()

            if current_timestamp <= modified_since:
                response = HTTPNotModified()
                self._add_timestamp_header(response)
                raise response

    def _raise_412_if_modified(self, record=None):
        """Raise 412 if current timestamp is superior to the one
        specified in headers.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed`
        """
        unmodified_since = self.request.headers.get('If-Unmodified-Since')

        if unmodified_since:
            unmodified_since = int(unmodified_since)

            if record:
                current_timestamp = record[self.collection.modified_field]
            else:
                current_timestamp = self.collection.timestamp()

            if current_timestamp > unmodified_since:
                error_msg = 'Resource was modified meanwhile'
                response = http_error(HTTPPreconditionFailed(),
                                      errno=ERRORS.MODIFIED_MEANWHILE,
                                      message=error_msg)
                self._add_timestamp_header(response)
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
