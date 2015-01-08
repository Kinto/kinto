import time

from cornice.resource import resource
from pyramid.security import Authenticated

import colander
from colander import SchemaNode, String, null

from readinglist.resource import BaseResource, RessourceSchema


class TimeStamp(SchemaNode):
    """Basic integer field that takes current timestamp if no value
    is provided.
    """
    schema_type = colander.Integer
    title = 'Epoch timestamp'

    def deserialize(self, cstruct):
        if cstruct is null and self.required:
            cstruct = int(time.time())
        return super(TimeStamp, self).deserialize(cstruct)


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

    stored_on = TimeStamp()
    last_modified = TimeStamp()

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

    def deserialize(self, cstruct):
        """Deserialization overrides that allow values manipulation between
        several fields.

        Currently, article content is not fetched, thus resolved url and title
        are the ones provided.
        """
        cstruct['resolved_title'] = cstruct.get('title')
        cstruct['resolved_url'] = cstruct.get('url')
        return super(ArticleSchema, self).deserialize(cstruct)


@resource(collection_path='/articles',
          path='/articles/{id}',
          description='Collection of articles',
          permission=Authenticated)
class Article(BaseResource):
    mapping = ArticleSchema()
