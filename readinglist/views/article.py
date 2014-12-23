from cornice.resource import resource
from pyramid.security import Authenticated
from colander import SchemaNode, String

from readinglist.resource import BaseResource, RessourceSchema


class ArticleSchema(RessourceSchema):
    url = SchemaNode(String())
    title = SchemaNode(String())


@resource(collection_path='/articles',
          path='/articles/{id}',
          description='Collection of articles',
          permission=Authenticated)
class Article(BaseResource):
    mapping = ArticleSchema()
