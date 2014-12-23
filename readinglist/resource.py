import json

import pyramid.httpexceptions
import colander

from readinglist.backend.exceptions import RecordNotFoundError


def exists_or_404():
    """View decorator to catch unknown record errors in backend."""
    def wrap(view):
        def wrapped_view(self, *args, **kwargs):
            try:
                return view(self, *args, **kwargs)
            except RecordNotFoundError as e:
                self.request.errors.add('path', 'id', str(e))
                self.request.errors.status = "404 Resource Not Found"
        return wrapped_view
    return wrap


class RessourceSchema(colander.MappingSchema):
    _id = colander.SchemaNode(colander.String(), missing=colander.drop)

    def schema_type(self, **kwargs):
        return colander.Mapping(unknown='preserve')


class BaseResource(object):

    mapping = RessourceSchema()

    @classmethod
    def resource_name(cls):
        return cls.__name__.lower()

    def __init__(self, request):
        self.request = request
        self.db = request.db
        self.db_kwargs = dict(resource=self.resource_name(),
                              user_id=request.authenticated_userid)

    def deserialize(self, raw):
        return json.loads(raw)

    def validate(self, record):
        # XXX: how to use cls.mapping in cornice decorators
        # instead of custom code here ?
        try:
            return self.mapping.deserialize(record)
        except colander.Invalid as e:
            self.request.errors.add('path', 'id', str(e))
            raise pyramid.httpexceptions.HTTPBadRequest()

    #
    # End-points
    #

    def collection_get(self):
        records = self.db.get_all(**self.db_kwargs)
        body = {
            '_items': records
        }
        return body

    def collection_post(self):
        record = self.deserialize(self.request.body)
        record = self.validate(record)
        record = self.db.create(record=record, **self.db_kwargs)
        return record

    @exists_or_404()
    def get(self):
        record_id = self.request.matchdict['id']
        record = self.db.get(record_id=record_id, **self.db_kwargs)
        return record

    @exists_or_404()
    def patch(self):
        record_id = self.request.matchdict['id']

        original = self.db.get(record_id=record_id, **self.db_kwargs)
        modified = self.deserialize(self.request.body)
        updated = original.copy()
        updated.update(**modified)

        updated = self.validate(updated)

        record = self.db.update(record_id=record_id,
                                record=updated,
                                **self.db_kwargs)

        return record

    @exists_or_404()
    def delete(self):
        record_id = self.request.matchdict['id']
        record = self.db.delete(record_id=record_id, **self.db_kwargs)
        return record
