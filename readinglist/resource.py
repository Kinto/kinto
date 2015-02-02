import re

import colander
from cornice import resource
from cornice.schemas import CorniceSchema
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound)
import six

from readinglist.backend.exceptions import RecordNotFoundError
from readinglist import errors
from readinglist.utils import COMPARISON, native_value, msec_time


class TimeStamp(colander.SchemaNode):
    """Basic integer field that takes current timestamp if no value
    is provided.
    """
    schema_type = colander.Integer
    title = 'Epoch timestamp'
    auto_now = True
    missing = None

    def deserialize(self, cstruct=colander.null):
        if cstruct is colander.null and self.auto_now:
            cstruct = msec_time()
        return super(TimeStamp, self).deserialize(cstruct)


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
                      error_handler=errors.json_error,
                      cors_origins=('*',),
                      depth=2)
        params.update(**kwargs)

        return resource.resource(**params)(klass)
    return wrapper


class RessourceSchema(colander.MappingSchema):
    """Base resource schema.

    It brings common fields and behaviour for all inherited schemas.
    """
    _id = colander.SchemaNode(colander.String(), missing=colander.drop)
    last_modified = TimeStamp()

    class Options:
        readonly_fields = ('_id', 'last_modified')

    def is_readonly(self, field):
        """Return True if specified field name is read-only."""
        return field in self.Options.readonly_fields


class BaseResource(object):

    mapping = RessourceSchema()
    id_field = '_id'
    modified_field = 'last_modified'
    schema_for = ('POST', 'PUT')

    def __init__(self, request):
        self.request = request
        self.db = request.db
        self.db_kwargs = dict(resource=self,
                              user_id=request.authenticated_userid)
        self.known_fields = [c.name for c in self.mapping.children]
        self.timestamp = self.db.last_collection_timestamp(**self.db_kwargs)

    @property
    def schema(self):
        colander_schema = self.mapping

        if self.request.method not in self.schema_for:
            # No-op since payload is not validated against schema
            colander_schema = colander.MappingSchema(unknown='preserve')

        return CorniceSchema.from_colander(colander_schema)

    def fetch_record(self):
        """Fetch current view related record, and raise 404 if missing."""
        try:
            record_id = self.request.matchdict['id']
            return self.db.get(record_id=record_id,
                               **self.db_kwargs)
        except RecordNotFoundError:
            response = HTTPNotFound(
                body=errors.format_error(
                    code=HTTPNotFound.code,
                    errno=errors.ERRORS.INVALID_RESOURCE_ID,
                    error=HTTPNotFound.title),
                content_type='application/json')
            raise response

    def process_record(self, new, old=None):
        """Hook to post-process records and introduce specific logics
        or validation.
        """
        new = self.preprocess_record(new, old)
        return new

    def preprocess_record(self, new, old=None):
        return new

    def merge_fields(self, record, changes):
        """Merge changes into current record fields.
        """
        for field in changes.keys():
            if self.mapping.is_readonly(field):
                error = 'Cannot modify {0}'.format(field)
                self.request.errors.add('body', name=field, description=error)
                raise errors.json_error(self.request.errors)

        updated = record.copy()
        updated.update(**changes)
        return self.validate(updated)

    def validate(self, record):
        """Validate specified record against resource schema.
        Raise 400 if not valid."""
        try:
            return self.mapping.deserialize(record)
        except colander.Invalid as e:
            # Transform the errors we got from colander into cornice errors
            for field, error in e.asdict().items():
                self.request.errors.add('body', name=field, description=error)
            raise errors.json_error(self.request.errors)

    def add_timestamp_header(self, response):
        """Add current timestamp in response headers, when request comes in.
        """
        timestamp = six.text_type(self.timestamp).encode('utf-8')
        response.headers['Last-Modified'] = timestamp

    def raise_304_if_not_modified(self, record=None):
        """Raise 304 if current timestamp is inferior to the one specified
        in headers."""
        modified_since = self.request.headers.get('If-Modified-Since')

        if modified_since:
            modified_since = int(modified_since)

            if record:
                current_timestamp = record[self.modified_field]
            else:
                current_timestamp = self.db.last_collection_timestamp(
                    **self.db_kwargs)

            if current_timestamp <= modified_since:
                response = HTTPNotModified()
                self.add_timestamp_header(response)
                raise response

    def raise_412_if_modified(self, record=None):
        """Raise 412 if current timestamp is superior to the one
        specified in headers."""
        unmodified_since = self.request.headers.get('If-Unmodified-Since')

        if unmodified_since:
            unmodified_since = int(unmodified_since)

            if record:
                current_timestamp = record[self.modified_field]
            else:
                current_timestamp = self.db.last_collection_timestamp(
                    **self.db_kwargs)

            if current_timestamp > unmodified_since:
                error_msg = 'Resource was modified meanwhile'
                response = HTTPPreconditionFailed(
                    body=errors.format_error(
                        code=HTTPPreconditionFailed.code,
                        errno=errors.ERRORS.MODIFIED_MEANWHILE,
                        error=HTTPPreconditionFailed.title,
                        message=error_msg),
                    content_type='application/json')
                self.add_timestamp_header(response)
                raise response

    def _extract_filters(self, queryparams):
        """Extracts filters from QueryString parameters."""
        filters = []

        for param, value in queryparams.items():
            param = param.strip()
            value = native_value(value)

            if param == '_sort':
                continue

            if param == '_since':
                if not isinstance(value, six.integer_types):
                    error_details = {
                        'name': param,
                        'location': 'querystring',
                        'description': 'Invalid value for _since'
                    }
                    self.request.errors.add(**error_details)
                    raise errors.json_error(self.request.errors)

                filters.append(
                    (self.modified_field, value, COMPARISON.GT)
                )
                continue

            m = re.match(r'^(min|max|not)_(\w+)$', param)
            if m:
                keyword, field = m.groups()
                operator = getattr(COMPARISON, keyword.upper())
            else:
                operator, field = COMPARISON.EQ, param

            if field not in self.known_fields:
                error_details = {
                    'name': None,
                    'location': 'querystring',
                    'description': "Unknown filter field '{0}'".format(param)
                }
                self.request.errors.add(**error_details)
                return

            filters.append((field, value, operator))

        return filters

    def _extract_sorting(self, queryparams):
        """Extracts filters from QueryString parameters."""
        specified = queryparams.get('_sort', '').split(',')
        sorting = []
        for field in specified:
            field = field.strip()
            m = re.match(r'^([\-+]?)(\w+)$', field)
            if m:
                order, field = m.groups()

                if field not in self.known_fields:
                    error_details = {
                        'name': None,
                        'location': 'querystring',
                        'description': "Unknown sort field '{0}'".format(field)
                    }
                    self.request.errors.add(**error_details)
                    raise errors.json_error(self.request.errors)

                direction = -1 if order == '-' else 1
                sorting.append((field, direction))

        return sorting

    #
    # End-points
    #

    @resource.view(permission='readonly')
    def collection_get(self):
        self.add_timestamp_header(self.request.response)
        self.raise_304_if_not_modified()
        self.raise_412_if_modified()

        filters = self._extract_filters(self.request.GET)
        sorting = self._extract_sorting(self.request.GET)
        records = self.db.get_all(filters=filters,
                                  sorting=sorting,
                                  **self.db_kwargs)

        total_records = six.text_type(len(records)).encode('utf-8')
        self.request.response.headers['Total-Records'] = total_records

        body = {
            'items': records,
        }
        return body

    @resource.view(permission='readwrite')
    def collection_post(self):
        self.raise_412_if_modified()

        new_record = self.process_record(self.request.validated)
        record = self.db.create(record=new_record, **self.db_kwargs)
        self.request.response.status_code = 201
        return record

    @resource.view(permission='readonly')
    def get(self):
        self.add_timestamp_header(self.request.response)
        record = self.fetch_record()
        self.raise_304_if_not_modified(record)
        self.raise_412_if_modified(record)

        return record

    @resource.view(permission='readwrite')
    def put(self):
        record_id = self.request.matchdict['id']

        try:
            existing = self.db.get(record_id=record_id,
                                   **self.db_kwargs)
            self.raise_412_if_modified(existing)
        except RecordNotFoundError:
            existing = None

        new_record = self.request.validated
        new_record = self.process_record(new_record, old=existing)
        record = self.db.update(record_id=record_id,
                                record=new_record,
                                **self.db_kwargs)
        return record

    @resource.view(permission='readwrite')
    def patch(self):
        record = self.fetch_record()
        self.raise_412_if_modified(record)

        updated = self.merge_fields(record, changes=self.request.json)

        updated = self.process_record(updated, old=record)

        record = self.db.update(record_id=record[self.id_field],
                                record=updated,
                                **self.db_kwargs)
        return record

    @resource.view(permission='readwrite')
    def delete(self):
        record = self.fetch_record()
        self.raise_412_if_modified(record)

        self.db.delete(record_id=record[self.id_field], **self.db_kwargs)
        return record
