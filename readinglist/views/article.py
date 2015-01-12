from cornice.resource import resource
from pyramid.security import Authenticated

import colander
from colander import SchemaNode, String, null

from readinglist.resource import BaseResource, RessourceSchema, TimeStamp


# removes whitespace, newlines, and tabs from the beginning/end of a string
strip_whitespace = lambda v: v.strip(' \t\n\r') if v is not null else v


class DeviceName(SchemaNode):
    """String representing the device name."""
    schema_type = String
    validator = colander.Length(min=1)

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)


class ArticleSchema(RessourceSchema):

    url = SchemaNode(String(),
                     preparer=strip_whitespace,
                     validator=colander.url)
    title = SchemaNode(String(),
                       preparer=strip_whitespace,
                       validator=colander.Length(min=1))
    added_by = DeviceName()
    added_on = TimeStamp()
    stored_on = TimeStamp()

    status = SchemaNode(colander.Integer(), missing=0)
    favorite = SchemaNode(colander.Boolean(), missing=False)
    unread = SchemaNode(colander.Boolean(), missing=True)
    is_article = SchemaNode(colander.Boolean(), missing=True)
    excerpt = SchemaNode(String(), missing="")

    marked_read_by = DeviceName(missing=None)
    marked_read_on = TimeStamp(missing=None)
    word_count = SchemaNode(colander.Integer(), missing=None)
    resolved_url = SchemaNode(String(), missing=None)
    resolved_title = SchemaNode(String(), missing=None)


@resource(collection_path='/articles',
          path='/articles/{id}',
          description='Collection of articles',
          permission=Authenticated)
class Article(BaseResource):
    mapping = ArticleSchema()

    def validate(self, record):
        """Currently, article content is not fetched, thus resolved url
        and title are the ones provided.
        """
        validated = super(Article, self).validate(record)

        validated['resolved_title'] = validated['title']
        validated['resolved_url'] = validated['url']

        if validated['unread']:
            validated['marked_read_on'] = None
            validated['marked_read_by'] = None

        return validated