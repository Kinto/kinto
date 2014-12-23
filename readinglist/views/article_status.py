from cornice.resource import resource
from pyramid.security import Authenticated
from colander import SchemaNode, String, Int

from readinglist.backend.exceptions import RecordNotFoundError
from readinglist.resource import BaseResource, exists_or_404, RessourceSchema


class DeviceStatus(RessourceSchema):
    article_id = SchemaNode(String())
    device_id = SchemaNode(String())
    read = device_id = SchemaNode(Int())


@resource(collection_path='/articles/{id}/status',
          path='/articles/{id}/status/{device_id}',
          description='Article status by device',
          permission=Authenticated)
class ArticleStatus(BaseResource):
    mapping = DeviceStatus()

    def get_article(self):
        """Helper to get related article record."""
        article_id = self.request.matchdict['id']
        db_kwargs = self.db_kwargs.copy()
        db_kwargs.update(resource='article')
        article = self.request.db.get(record_id=article_id, **db_kwargs)
        return article

    def get_article_status(self):
        """Helper to get status of this article for this device.

        :note:
            Status records are unique by (article, device).
        """
        device_id = self.request.matchdict['device_id']
        article = self.get_article()
        all_statuses = self.request.db.get_all(**self.db_kwargs)
        for status in all_statuses:
            match = ((status['article_id'], status['device_id']) ==
                     (article['_id'], device_id))
            if match:
                return status
        raise RecordNotFoundError('Status {} not found.'.format(device_id))

    @exists_or_404()
    def collection_post(self):
        status = self.deserialize(self.request.body)

        # Link to current article
        article = self.get_article()
        status['article_id'] = article['_id']

        status = self.validate(status)

        status = self.request.db.create(record=status, **self.db_kwargs)
        return status

    @exists_or_404()
    def get(self):
        return self.get_article_status()

    @exists_or_404()
    def patch(self):
        record = self.get_article_status()
        record_id = record['_id']

        modified = self.deserialize(self.request.body)
        updated = record.copy()
        updated.update(**modified)

        updated = self.validate(updated)

        record = self.request.db.update(record_id=record_id,
                                        record=updated,
                                        **self.db_kwargs)
        return record

    @exists_or_404()
    def delete(self):
        record = self.get_article_status()
        record_id = record['_id']
        record = self.request.db.delete(record_id=record_id, **self.db_kwargs)
        return record
