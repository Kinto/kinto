import re
import inspect

import six
import colander
from cornice import resource

from readinglist.backend.exceptions import RecordNotFoundError
from readinglist.errors import json_error, ImmutableFieldError
from readinglist.utils import COMPARISON, native_value, msec_time


def exists_or_404():
    """View decorator to catch unknown record errors in backend."""
    def wrap(view):
        def wrapped_view(self, *args, **kwargs):
            try:
                return view(self, *args, **kwargs)
            except RecordNotFoundError as e:
                self.request.errors.add('path', 'id', six.text_type(e))
                self.request.errors.status = 404
        return wrapped_view
    return wrap


def validates_or_400():
    """View decorator to catch validation errors and return 400 responses."""
    def wrap(view):
        def wrapped_view(self, *args, **kwargs):
            try:
                return view(self, *args, **kwargs)
            except ValueError as e:
                error = "Invalid JSON request body: " + six.text_type(e)
                self.request.errors.add('body', name=None, description=error)
            except ImmutableFieldError as e:
                self.request.errors.add('body', e.field, six.text_type(e))
            except colander.Invalid as e:
                # Transform the errors we got from colander into cornice errors
                for field, error in e.asdict().items():
                    self.request.errors.add('body', field, error)
            self.request.errors.status = 400
        return wrapped_view
    return wrap


def refresh_timestamp():
    """View decorator to refresh the request timestamp, because it was
    incremented during the view execution."""
    def wrap(view):
        def wrapped_view(self, *args, **kwargs):
            result = view(self, *args, **kwargs)
            user_id = self.request.authenticated_userid
            self.request.timestamp = self.db.timestamp(user_id)
            return result
        return wrapped_view
    return wrap


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
                      error_handler=json_error,
                      depth=2)
        params.update(**kwargs)

        # Inject resource schema in views decorators arguments
        for name, method in inspect.getmembers(klass):
            # Hack from Cornice ``@resource()`` and ``@view()`` decorator
            decorations = getattr(method, '__views__', [])
            for view_args in decorations:
                if view_args.pop('with_schema', False):
                    view_args['schema'] = klass.mapping

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

    def __init__(self, request):
        self.request = request
        self.db = request.db
        self.db_kwargs = dict(resource=self,
                              user_id=request.authenticated_userid)
        self.record = None
        self.known_fields = [c.name for c in self.mapping.children]

    def process_record(self, new, old=None):
        """Hook to post-process records and introduce specific logics
        or validation.
        """
        new = self.preprocess_record(new, old)
        return new

    def preprocess_record(self, new, old=None):
        return new

    def validate(self, record):
        return self.mapping.deserialize(record)

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
                    return

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
                    return

                direction = -1 if order == '-' else 1
                sorting.append((field, direction))

        return sorting

    def merge_fields(self, changes):
        """Merge changes into current record fields.

        :raises ImmutableFieldError: if some field is read-only.
        """
        for field in changes.keys():
            if self.mapping.is_readonly(field):
                raise ImmutableFieldError(field)

        updated = self.record.copy()
        updated.update(**changes)
        return self.validate(updated)

    #
    # End-points
    #

    @resource.view(permission='readonly')
    def collection_get(self):
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

    @resource.view(permission='readwrite', with_schema=True)
    @refresh_timestamp()
    def collection_post(self):
        new_record = self.process_record(self.request.validated)
        self.record = self.db.create(record=new_record, **self.db_kwargs)
        self.request.response.status_code = 201
        return self.record

    @resource.view(permission='readonly')
    @exists_or_404()
    def get(self):
        record_id = self.request.matchdict['id']
        self.record = self.db.get(record_id=record_id, **self.db_kwargs)
        return self.record

    @resource.view(permission='readwrite', with_schema=True)
    @refresh_timestamp()
    def put(self):
        record_id = self.request.matchdict['id']

        try:
            self.record = self.db.get(record_id=record_id, **self.db_kwargs)
        except RecordNotFoundError:
            self.record = None

        new_record = self.request.validated
        new_record = self.process_record(new_record, old=self.record)
        self.record = self.db.update(record_id=record_id,
                                     record=new_record,
                                     **self.db_kwargs)
        return self.record

    @resource.view(permission='readwrite')
    @exists_or_404()
    @validates_or_400()
    @refresh_timestamp()
    def patch(self):
        record_id = self.request.matchdict['id']
        self.record = self.db.get(record_id=record_id, **self.db_kwargs)

        updated = self.merge_fields(changes=self.request.json)

        updated = self.process_record(updated, old=self.record)

        record = self.db.update(record_id=record_id,
                                record=updated,
                                **self.db_kwargs)
        return record

    @resource.view(permission='readwrite')
    @exists_or_404()
    @refresh_timestamp()
    def delete(self):
        record_id = self.request.matchdict['id']
        self.record = self.db.delete(record_id=record_id, **self.db_kwargs)
        return self.record
