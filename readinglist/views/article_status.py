import json

from cornice.resource import resource
from pyramid.security import Authenticated

from readinglist.backend.exceptions import RecordNotFoundError
from readinglist.resource import BaseResource, exists_or_404


@resource(collection_path='/articles/{id}/status',
          path='/articles/{id}/status/{device_id}',
          description='Article status by device',
          permission=Authenticated)
class ArticleStatus(BaseResource):

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
        status = json.loads(self.request.body)

        # Link to current article
        article = self.get_article()
        status['article_id'] = article['_id']

        status = self.request.db.create(record=status, **self.db_kwargs)
        return status

    @exists_or_404()
    def get(self):
        return self.get_article_status()

    @exists_or_404()
    def patch(self):
        record = self.get_article_status()
        record_id = record['_id']
        modified = json.loads(self.request.body)
        record = self.request.db.update(record_id=record_id,
                                        record=modified,
                                        **self.db_kwargs)
        return record

    @exists_or_404()
    def delete(self):
        record = self.get_article_status()
        record_id = record['_id']
        record = self.request.db.delete(record_id=record_id, **self.db_kwargs)
        return record
