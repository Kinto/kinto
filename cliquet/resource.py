import re

import colander
from cornice import resource
from cornice.schemas import CorniceSchema
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPMethodNotAllowed,
                                    HTTPNotFound, HTTPConflict)
import six

from cliquet import logger
from cliquet.storage import exceptions as storage_exceptions, Filter, Sort
from cliquet.errors import (http_error, raise_invalid, ERRORS,
                            json_error_handler)
from cliquet.schema import ResourceSchema
from cliquet.utils import (
    COMPARISON, classname, native_value, decode64, encode64, json,
    current_service
)


def crud(**kwargs):
    """
    Decorator for resource classes.

    By default, the lower class name of the resource is used to build URLs.

    This decorator accepts the same parameters as the :rtd:`Cornice <cornice>`
    :meth:`~cornice:cornice.resource.resource` decorator.

    .. code-block:: python

            from cliquet import resource

            @resource.crud(collection_path='/stories',
                           path='/stories/{id}',
                           description='My favorite stories')
            class Story(resource.BaseResource):
                ...
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


class Collection(object):
    """A collection stores and manipulate records in its attached storage.

    It is not aware of HTTP environment nor protocol.

    Records are isolated according to the provided `name` and `parent_id`.

    Those notions have no particular semantic and can represent anything.
    For example, the resource `name` can be the *type* of objects stored, and
    `parent_id` can be the current *user id* or *a group* where the collection
    belongs. If left empty, the collection records are not isolated.
    """
    id_field = 'id'
    """Name of `id` field in records"""

    modified_field = 'last_modified'
    """Name of `last modified` field in records"""

    deleted_field = 'deleted'
    """Name of `deleted` field in deleted records"""

    def __init__(self, storage, id_generator=None, name='', parent_id='',
                 auth=None):
        """
        :param storage: an instance of storage
        :type storage: :class:`cliquet.storage.Storage`
        :param id_generator: an instance of id generator, used by storage
            on record creation.

        :param str name: the resource name
        :param str parent_id: the default parent id
        """
        self.storage = storage
        self.id_generator = id_generator
        self.parent_id = parent_id
        self.name = name
        self.auth = auth

    def timestamp(self, parent_id=None):
        """Fetch the collection current timestamp.

        :param str parent_id: optional filter for parent id
        :rtype: integer
        """
        parent_id = parent_id or self.parent_id
        return self.storage.collection_timestamp(resource_name=self.name,
                                                 user_id=parent_id,  # XXX
                                                 auth=self.auth)

    def get_records(self, filters=None, sorting=None, pagination_rules=None,
                    limit=None, include_deleted=False, parent_id=None):
        """Fetch the collection records.

        Override to post-process records after feching them from storage.

        :param filters: Optionally filter the records by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `cliquet.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of :class:`cliquet.storage.Filter`

        :param sorting: Optionnally sort the records by attribute.
            Each sort instruction in this list refers to a field and a
            direction (negative means descending). All sort instructions are
            cumulative.
        :type sorting: list of :class:`cliquet.storage.Sort`

        :param pagination_rules: Optionnally paginate the list of records.
            This list of rules aims to reduce the set of records to the current
            page. A rule is a list of filters (see `filters` parameter),
            and all rules are combined using *OR*.
        :type pagination_rules: list of list of :class:`cliquet.storage.Filter`

        :param int limit: Optionnally limit the number of records to be
            retrieved.

        :param bool include_deleted: Optionnally include the deleted records
            that match the filters.

        :param str parent_id: optional filter for parent id

        :returns: A tuple with the list of records in the current page,
            the total number of records in the result set.
        :rtype: tuple
        """
        parent_id = parent_id or self.parent_id
        records, total_records = self.storage.get_all(
            resource_name=self.name,
            user_id=parent_id,  # XXX: rename.
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            include_deleted=include_deleted,
            id_field=self.id_field,
            modified_field=self.modified_field,
            deleted_field=self.deleted_field,
            auth=self.auth)
        return records, total_records

    def delete_records(self, filters=None, parent_id=None):
        """Delete multiple collection records.

        Override to post-process records after their deletion from storage.

        :param filters: Optionally filter the records by their attribute.
            Each filter in this list is a tuple of a field, a value and a
            comparison (see `cliquet.utils.COMPARISON`). All filters
            are combined using *AND*.
        :type filters: list of :class:`cliquet.storage.Filter`

        :param str parent_id: optional filter for parent id

        :returns: The list of deleted records from storage.
        """
        parent_id = parent_id or self.parent_id
        return self.storage.delete_all(resource_name=self.name,
                                       user_id=parent_id,  # XXX: merge.
                                       filters=filters,
                                       id_field=self.id_field,
                                       modified_field=self.modified_field,
                                       deleted_field=self.deleted_field,
                                       auth=self.auth)

    def get_record(self, record_id, parent_id=None):
        """Fetch current view related record, and raise 404 if missing.

        :param str record_id: record identifier
        :param str parent_id: optional filter for parent id

        :returns: the record from storage
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        return self.storage.get(resource_name=self.name,
                                user_id=parent_id,  # XXX: rename.
                                record_id=record_id,
                                id_field=self.id_field,
                                modified_field=self.modified_field,
                                auth=self.auth)

    def create_record(self, record, parent_id=None, unique_fields=None):
        """Create a record in the collection.

        Override to perform actions or post-process records after their
        creation in storage.

        .. code-block:: python

            def create_record(self, record):
                record = super(MyResource, self).create_record(record)
                idx = index.store(record)
                record['index'] = idx
                return record

        :param dict record: record to store
        :param str parent_id: optional filter for parent id
        :param tuple unique_fields: list of fields that should remain unique

        :returns: the newly created record.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        return self.storage.create(resource_name=self.name,
                                   user_id=parent_id,  # XXX: rename.
                                   record=record,
                                   id_generator=self.id_generator,
                                   unique_fields=unique_fields,
                                   id_field=self.id_field,
                                   modified_field=self.modified_field,
                                   auth=self.auth)

    def update_record(self, record, parent_id=None, unique_fields=None):
        """Update a record in the collection.

        Override to perform actions or post-process records after their
        modification in storage.

        .. code-block:: python

            def update_record(self, record, parent_id=None,unique_fields=None):
                record = super(MyCollection, self).update_record(record,
                                                                 parent_id,
                                                                 unique_fields)
                subject = 'Record {} was changed'.format(record[self.id_field])
                send_email(subject)
                return record

        :param dict record: record to store
        :param str parent_id: optional filter for parent id
        :param tuple unique_fields: list of fields that should remain unique
        :returns: the updated record.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        record_id = record[self.id_field]
        return self.storage.update(resource_name=self.name,
                                   user_id=parent_id,  # XXX: rename.
                                   record_id=record_id,
                                   record=record,
                                   unique_fields=unique_fields,
                                   id_field=self.id_field,
                                   modified_field=self.modified_field,
                                   auth=self.auth)

    def delete_record(self, record, parent_id=None):
        """Delete a record in the collection.

        Override to perform actions or post-process records after deletion
        from storage for example:

        .. code-block:: python

            def delete_record(self, record):
                deleted = super(MyCollection, self).delete_record(record)
                erase_media(record)
                deleted['media'] = 0
                return deleted

        :param dict record: the record to delete
        :param dict record: record to store
        :param str parent_id: optional filter for parent id
        :returns: the deleted record.
        :rtype: dict
        """
        parent_id = parent_id or self.parent_id
        record_id = record[self.id_field]
        return self.storage.delete(resource_name=self.name,
                                   user_id=parent_id,  # XXX: rename.
                                   record_id=record_id,
                                   id_field=self.id_field,
                                   modified_field=self.modified_field,
                                   deleted_field=self.deleted_field,
                                   auth=self.auth)


class BaseResource(object):
    """Base resource class providing every endpoint."""

    mapping = ResourceSchema()
    """Schema to validate records."""

    validate_schema_for = ('POST', 'PUT')
    """HTTP verbs for which the schema must be validated"""

    def __init__(self, request):
        # Collections are isolated by user.
        parent_id = request.authenticated_userid
        # Authentication to storage is transmitted as is (cf. cloud_storage).
        auth = request.headers.get('Authorization')

        self.collection = Collection(
            storage=request.registry.storage,
            id_generator=request.registry.id_generator,
            name=classname(self),
            parent_id=parent_id,
            auth=auth)

        self.request = request
        self.timestamp = self.collection.timestamp()
        self.record_id = self.request.matchdict.get('id')

        # Log resource context.
        logger.bind(resource_name=self.collection.name,
                    resource_timestamp=self.timestamp)

    @property
    def schema(self):
        """Resource schema, depending on HTTP verb.

        :returns: a :class:`~cornice:cornice.schemas.CorniceSchema` object
            built from this resource :attr:`mapping <.BaseResource.mapping>`.
        """
        colander_schema = self.mapping

        if self.request.method not in self.validate_schema_for:
            # No-op since payload is not validated against schema
            colander_schema = colander.MappingSchema(unknown='preserve')

        return CorniceSchema.from_colander(colander_schema, bind_request=False)

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

    @resource.view(
        permission='readonly',
        cors_headers=('Next-Page', 'Total-Records', 'Last-Modified')
    )
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

    @resource.view(permission='readwrite')
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
            :meth:`cliquet.resource.BaseResource.process_record` or
            :meth:`cliquet.resource.BaseResource.create_record`
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

    @resource.view(permission='readwrite')
    def collection_delete(self):
        """Collection ``DELETE`` endpoint: delete multiple records.

        Can be disabled via ``cliquet.delete_collection_enabled`` setting.

        :raises:
            :exc:`~pyramid:pyramid.httpexceptions.HTTPPreconditionFailed` if
            ``If-Unmodified-Since`` header is provided and collection modified
            in the iterim.

        :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPBadRequest`
            if filters are invalid.

        .. seealso::

            Add custom behaviour by overriding
            :meth:`cliquet.resource.BaseResource.delete_records`.
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

    @resource.view(permission='readonly', cors_headers=('Last-Modified',))
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

        .. seealso::

            Add custom behaviour by overriding
            :meth:`cliquet.resource.BaseResource.get_record`.
        """
        self._raise_400_if_invalid_id(self.record_id)
        self._add_timestamp_header(self.request.response)
        record = self._get_record_or_404(self.record_id)
        self._raise_304_if_not_modified(record)
        self._raise_412_if_modified(record)
        return record

    @resource.view(permission='readwrite')
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

    @resource.view(permission='readwrite')
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

    @resource.view(permission='readwrite')
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
            return self.collection.get_record(self.record_id)
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
