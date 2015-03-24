import re

import colander
from cornice import resource
from cornice.schemas import CorniceSchema
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPMethodNotAllowed,
                                    HTTPNotFound, HTTPConflict)
import six
from six.moves.urllib.parse import urlencode

from cliquet import logger
from cliquet.storage import exceptions as storage_exceptions, Filter, Sort
from cliquet.errors import (http_error, raise_invalid, ERRORS,
                            json_error_handler)
from cliquet.schema import ResourceSchema
from cliquet.utils import (
    COMPARISON, classname, native_value, decode_token, encode_token
)


def crud(**kwargs):
    """
    Decorator for resource classes.

    This allows to bring default parameters for Cornice ``resource()``.
    """
    def wrapper(klass):
        resource_name = klass.__name__.lower()
        params = dict(collection_path='/{0}s'.format(resource_name),
                      path='/{0}s/{{id}}'.format(resource_name),
                      description='Collection of {0}'.format(resource_name),
                      error_handler=json_error_handler,
                      cors_origins=('*',),
                      depth=2)
        params.update(**kwargs)

        return resource.resource(**params)(klass)
    return wrapper


class BaseResource(object):
    """Base resource class providing every endpoint."""
    mapping = ResourceSchema()
    """Schema to validate records"""

    validate_schema_for = ('POST', 'PUT')
    """HTTP verbs for which the schema must be validated"""

    id_field = 'id'
    """Name of *id* field in resource schema"""

    modified_field = 'last_modified'
    """Name of *last modified* field in resource schema"""

    deleted_field = 'deleted'
    """Field and value of deleted status in records"""

    def __init__(self, request):
        self.request = request
        self.db = request.db
        self.db_kwargs = dict(resource=self,
                              user_id=request.authenticated_userid)
        self.timestamp = self.db.collection_timestamp(**self.db_kwargs)
        self.record_id = self.request.matchdict.get('id')
        # Log resource context.
        logger.bind(resource_name=self.name, resource_timestamp=self.timestamp)

    @property
    def name(self):
        """Resource name, unique."""
        return classname(self)

    @property
    def schema(self):
        """Resource schema, depending on HTTP verb."""
        colander_schema = self.mapping

        if self.request.method not in self.validate_schema_for:
            # No-op since payload is not validated against schema
            colander_schema = colander.MappingSchema(unknown='preserve')

        return CorniceSchema.from_colander(colander_schema)

    def is_known_field(self, field):
        """Return the True if the field is defined in the resource mapping.
        :param field: Field name
        :type field: string
        :rtype: boolean

        """
        known_fields = [c.name for c in self.mapping.children] + \
                       [self.deleted_field]
        return field in known_fields

    #
    # End-points
    #

    @resource.view(
        permission='readonly',
        cors_headers=('Next-Page', 'Total-Records', 'Last-Modified')
    )
    def collection_get(self):
        """Collection `GET` endpoint."""
        self._add_timestamp_header(self.request.response)
        self._raise_304_if_not_modified()
        self._raise_412_if_modified()

        records, total_records, next_page = self.get_records()

        headers = self.request.response.headers
        headers['Total-Records'] = ('%s' % total_records).encode('utf-8')

        if next_page:
            headers['Next-Page'] = next_page.encode('utf-8')
        body = {
            'items': records,
        }

        return body

    @resource.view(permission='readwrite')
    def collection_post(self):
        """Collection `POST` endpoint."""
        self._raise_412_if_modified()

        new_record = self.process_record(self.request.validated)
        record = self.create_record(new_record)
        self.request.response.status_code = 201
        return record

    @resource.view(permission='readwrite')
    def collection_delete(self):
        """Collection `DELETE` endpoint."""
        settings = self.request.registry.settings
        enabled = settings['cliquet.delete_collection_enabled']
        if not enabled:
            # XXX: https://github.com/mozilla-services/cliquet/issues/46
            raise HTTPMethodNotAllowed()

        self._raise_412_if_modified()

        deleted = self.delete_records()

        body = {
            'items': deleted,
        }

        return body

    @resource.view(permission='readonly', cors_headers=('Last-Modified',))
    def get(self):
        """Record `GET` endpoint."""
        self._add_timestamp_header(self.request.response)
        record = self.get_record(self.record_id)
        self._raise_304_if_not_modified(record)
        self._raise_412_if_modified(record)

        return record

    @resource.view(permission='readwrite')
    def put(self):
        """Record `PUT` endpoint."""
        try:
            existing = self.get_record(self.record_id)
            self._raise_412_if_modified(existing)
        except HTTPNotFound:
            existing = None

        new_record = self.request.validated

        new_id = new_record.setdefault(self.id_field, self.record_id)
        if new_id != self.record_id:
            error_msg = 'Record id does not match existing record'
            error_details = {
                'name': self.id_field,
                'location': 'querystring',
                'description': error_msg
            }
            raise_invalid(self.request, **error_details)

        new_record = self.process_record(new_record, old=existing)
        record = self.update_record(existing, new_record)
        return record

    @resource.view(permission='readwrite')
    def patch(self):
        """Record `PATCH` endpoint."""
        record = self.get_record(self.record_id)
        self._raise_412_if_modified(record)

        if not self.request.body:
            error_details = {
                'description': 'Empty body'
            }
            raise_invalid(self.request, **error_details)

        changes = self.request.json

        updated = self.apply_changes(record, changes=changes)
        updated = self.process_record(updated, old=record)

        record = self.update_record(record, updated, changes)
        return record

    @resource.view(permission='readwrite')
    def delete(self):
        """Record `DELETE` endpoint."""
        record = self.get_record(self.record_id)
        self._raise_412_if_modified(record)

        deleted = self.delete_record(record)
        return deleted

    #
    # Storage
    #

    def get_records(self):
        """Fetch the collection records, using querystring arguments for
        sorting, filtering and pagination.

        Override to implement custom querystring parsing, or post-process
        records after their retrieval from storage.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest` if filters or
            sorting are invalid.
        :returns: A tuple with the list of records in the current page,
            the total number of records in the result set, and the next page
            url.
        :rtype: tuple
        """
        filters = self._extract_filters()
        sorting = self._extract_sorting()
        pagination_rules, limit = self._extract_pagination_rules_from_token(
            sorting)

        include_deleted = self.modified_field in [f.field for f in filters]

        records, total_records = self.db.get_all(
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            include_deleted=include_deleted,
            **self.db_kwargs)

        next_page = None
        if limit and len(records) == limit and total_records > limit:
            next_page = self._next_page_url(sorting, limit, records[-1])

        # Bind metric about response size.
        logger.bind(nb_records=len(records), limit=limit)

        return records, total_records, next_page

    def delete_records(self):
        """Delete the collection records, using request querystring for
        filtering.

        Override to implement custom querystring parsing, or post-process
        records after their deletion from storage.

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest` if filters or
            sorting are invalid.
        """
        filters = self._extract_filters()
        return self.db.delete_all(filters=filters, **self.db_kwargs)

    def get_record(self, record_id):
        """Fetch current view related record, and raise 404 if missing.

        :raises: :class:`pyramid.httpexceptions.HTTPNotFound`
        :returns: the record from storage
        :rtype: dict
        """
        try:
            return self.db.get(record_id=record_id,
                               **self.db_kwargs)
        except storage_exceptions.RecordNotFoundError:
            response = http_error(HTTPNotFound(),
                                  errno=ERRORS.INVALID_RESOURCE_ID)
            raise response

    def create_record(self, record):
        """Create a record in the collection.

        Override to perform actions or post-process records after their
        creation in storage.

        .. code-block :: python

            def create_record(self, record):
                record = super(MyResource, self).create_record(record)
                idx = index.store(record)
                record['index'] = idx
                return record

        :raises: :class:`pyramid.httpexceptions.HTTPConflict` if a unique
            field constraint is violated.

        """
        try:
            return self.db.create(record=record, **self.db_kwargs)
        except storage_exceptions.UnicityError as e:
            self._raise_conflict(e)

    def update_record(self, old, new, changes=None):
        """Update a record in the collection.

        Override to perform actions or post-process records after their
        modification in storage.

        .. code-block :: python

            def update_record(self, record, old=None):
                record = super(MyResource, self).update_record(record, old)
                subject = 'Record {} was changed'.format(record[self.id_field])
                send_email(subject)
                return record

        :raises: :class:`pyramid.httpexceptions.HTTPConflict` if a unique
            field constraint is violated.

        """
        if changes is not None:
            nothing_changed = not any([old.get(k) != new.get(k)
                                       for k in changes.keys()])
            if nothing_changed:
                return new

        record_id = new[self.id_field]
        try:
            return self.db.update(record_id=record_id,
                                  record=new,
                                  **self.db_kwargs)
        except storage_exceptions.UnicityError as e:
            self._raise_conflict(e)

    def delete_record(self, record):
        """Delete a record in the collection.

        Override to perform actions or post-process records after deletion
        from storage for example:

        .. code-block :: python

            def delete_record(self, record):
                deleted = super(Resource, self).delete_record(record)
                erase_media(record)
                deleted['media'] = 0
                return deleted

        :param record: the record to delete
        :type record: dict
        """
        record_id = record[self.id_field]
        return self.db.delete(record_id=record_id, **self.db_kwargs)

    def process_record(self, new, old=None):
        """Hook for processing records before they reach storage, to introduce
        specific logics on fields for example.

        .. code-block :: python

            def process_record(self, new, old=None):
                version = old['version'] if old else 0
                new['version'] = version + 1
                return new

        Or add extra validation based on request:

        .. code-block :: python

            def process_record(self, new, old=None):
                if new['browser'] not in request.headers['User-Agent']:
                    raise_invalid(self.request, name='browser', error='Wrong')
                return new

        :param new: the validated record to be created or updated.
        :type new: dict
        :param old: the old record to be updated,
            ``None`` for creation endpoints.
        :type old: dict
        """
        return new

    def apply_changes(self, record, changes):
        """Merge changes into current record fields.

        :note:
            This is used in the context of PATCH only.

        Override this to control field changes at record level, for example:

        .. code-block :: python

            def apply_changes(self, record, changes):
                # Ignore value change if inferior
                if record['position'] > changes.get('position', -1):
                    changes.pop('position', None)
                return super(MyResource, self).apply_changes(record, changes)

        :raises: :class:`pyramid.httpexceptions.HTTPBadRequest` if result does
            not comply with resource schema.
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

    def _add_timestamp_header(self, response):
        """Add current timestamp in response headers, when request comes in.
        """
        timestamp = six.text_type(self.timestamp).encode('utf-8')
        response.headers['Last-Modified'] = timestamp

    def _raise_304_if_not_modified(self, record=None):
        """Raise 304 if current timestamp is inferior to the one specified
        in headers.

        :raises: :class:`pyramid.httpexceptions.HTTPNotModified`
        """
        modified_since = self.request.headers.get('If-Modified-Since')

        if modified_since:
            modified_since = int(modified_since)

            if record:
                current_timestamp = record[self.modified_field]
            else:
                current_timestamp = self.db.collection_timestamp(
                    **self.db_kwargs)

            if current_timestamp <= modified_since:
                response = HTTPNotModified()
                self._add_timestamp_header(response)
                raise response

    def _raise_412_if_modified(self, record=None):
        """Raise 412 if current timestamp is superior to the one
        specified in headers.

        :raises: :class:`pyramid.httpexceptions.HTTPPreconditionFailed`
        """
        unmodified_since = self.request.headers.get('If-Unmodified-Since')

        if unmodified_since:
            unmodified_since = int(unmodified_since)

            if record:
                current_timestamp = record[self.modified_field]
            else:
                current_timestamp = self.db.collection_timestamp(
                    **self.db_kwargs)

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
        :raises: :class:`pyramid.httpexceptions.HTTPConflict`
        """
        field = exception.field
        existing = exception.record[self.id_field]
        message = 'Conflict of field {0} on record {1}'.format(field, existing)
        response = http_error(HTTPConflict(),
                              errno=ERRORS.CONSTRAINT_VIOLATED,
                              message=message)
        response.existing = exception.record
        raise response

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
                    Filter(self.modified_field, value, operator)
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
        modified_field_used = self.modified_field in specified
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
            sorting.append(Sort(self.modified_field, -1))
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

    def _extract_pagination_rules_from_token(self, sorting):
        """Get pagination params."""
        queryparams = self.request.GET
        paginate_by = self.request.registry.settings['cliquet.paginate_by']
        limit = queryparams.get('_limit', paginate_by)
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

        token = queryparams.get('_token', None)
        filters = []
        if token:
            try:
                last_record = decode_token(token)
                assert isinstance(last_record, dict)
            except (ValueError, TypeError, AssertionError):
                error_msg = '_token has invalid content'
                error_details = {
                    'location': 'querystring',
                    'description': error_msg
                }
                raise_invalid(self.request, **error_details)

            filters = self._build_pagination_rules(sorting, last_record)
        return filters, limit

    def _next_page_url(self, sorting, limit, last_record):
        """Build the Next-Page header from where we stopped."""
        queryparams = self.request.GET.copy()
        queryparams['_limit'] = limit
        queryparams['_token'] = self._build_pagination_token(
            sorting, last_record)

        port = ''
        if self.request.server_port != 80:
            port = ':%s' % self.request.server_port

        next_page = '{host}{port}{path}?{querystring}'
        return next_page.format(host=self.request.host_url,
                                port=port,
                                path=self.request.path_info,
                                querystring=urlencode(queryparams))

    def _build_pagination_token(self, sorting, last_record):
        """Build a pagination token.

        It is a base64 JSON object with the sorting fields values of
        the last_record.

        """
        token = {}

        for field, _ in sorting:
            token[field] = last_record[field]

        return encode_token(token)
