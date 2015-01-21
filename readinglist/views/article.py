import colander
from colander import SchemaNode, String

from readinglist.resource import crud, BaseResource, RessourceSchema, TimeStamp
from readinglist.utils import strip_whitespace


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
    marked_read_on = TimeStamp(auto_now=False)
    word_count = SchemaNode(colander.Integer(), missing=None)
    resolved_url = SchemaNode(String(), missing=None)
    resolved_title = SchemaNode(String(), missing=None)

    __readonly_fields__ = ('url', 'stored_on') \
        + RessourceSchema.__readonly_fields__


@crud()
class Article(BaseResource):
    mapping = ArticleSchema()

    def preprocess_record(self, new, old=None):
        """Currently, article content is not fetched, thus resolved url
        and title are the ones provided.
        """

        new['resolved_title'] = new['title']
        new['resolved_url'] = new['url']

        if new['unread']:
            # Article is not read
            new['marked_read_on'] = None
            new['marked_read_by'] = None

        return new
