import json

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


class BaseResource(object):

    @classmethod
    def resource_name(cls):
        return cls.__name__.lower()

    def __init__(self, request):
        self.request = request
        self.db_kwargs = dict(resource=self.resource_name(),
                              user_id=request.authenticated_userid)

    def collection_get(self):
        records = self.request.db.get_all(**self.db_kwargs)
        body = {
            '_items': records
        }
        return body

    def collection_post(self):
        record = json.loads(self.request.body)
        record = self.request.db.create(record=record, **self.db_kwargs)
        return record

    @exists_or_404()
    def get(self):
        record_id = self.request.matchdict['id']
        record = self.request.db.get(record_id=record_id, **self.db_kwargs)
        return record

    @exists_or_404()
    def patch(self):
        record_id = self.request.matchdict['id']
        record = json.loads(self.request.body)
        record = self.request.db.update(record_id=record_id,
                                        record=record,
                                        **self.db_kwargs)
        return record

    @exists_or_404()
    def delete(self):
        record_id = self.request.matchdict['id']
        record = self.request.db.delete(record_id=record_id, **self.db_kwargs)
        return record
