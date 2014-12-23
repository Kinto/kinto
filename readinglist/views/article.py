from cornice.resource import resource
from pyramid.security import Authenticated

from readinglist.resource import BaseResource


@resource(name='article',
          collection_path='/articles',
          path='/articles/{id}',
          description='Collection of articles',
          permission=Authenticated)
class Article(BaseResource):
    pass
