import colander
from colander import SchemaNode, String
from pyramid import httpexceptions

from readinglist.resource import crud, BaseResource, ResourceSchema, TimeStamp
from readinglist.utils import strip_whitespace


class DeviceName(SchemaNode):
    """String representing the device name."""
    schema_type = String
    validator = colander.Length(min=1)

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)


class URL(SchemaNode):
    """String representing a URL."""
    schema_type = String
    validator = colander.All(colander.url, colander.Length(min=1, max=2048))

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)


class ArticleTitle(SchemaNode):
    """String representing the title of an article."""
    schema_type = String
    validator = colander.Length(min=1, max=1024)

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)


class ArticleSchema(ResourceSchema):
    """Schema for a reading list article."""

    url = URL()
    title = ArticleTitle()
    added_by = DeviceName()
    added_on = TimeStamp()
    stored_on = TimeStamp()

    status = SchemaNode(colander.Integer(), missing=0,
                        validator=colander.Range(min=0, max=1))
    favorite = SchemaNode(colander.Boolean(), missing=False)
    unread = SchemaNode(colander.Boolean(), missing=True)
    is_article = SchemaNode(colander.Boolean(), missing=True)
    excerpt = SchemaNode(String(), missing="")

    read_position = SchemaNode(colander.Integer(), missing=0,
                               validator=colander.Range(min=0))
    marked_read_by = DeviceName(missing=None)
    marked_read_on = TimeStamp(auto_now=False)
    word_count = SchemaNode(colander.Integer(), missing=None)
    resolved_url = URL(missing=None)
    resolved_title = ArticleTitle(missing=None)

    class Options:
        readonly_fields = ('url', 'stored_on') + \
            ResourceSchema.Options.readonly_fields
        unique_fields = ('url', 'resolved_url')


@crud()
class Article(BaseResource):
    mapping = ArticleSchema()

    def preprocess_record(self, new, old=None):
        """Currently, article content is not fetched, thus resolved url
        and title are the ones provided.
        """
        if old:
            # Read position should be superior
            if old['read_position'] > new['read_position']:
                new['read_position'] = old['read_position']

            # Marking as read requires device info
            if old['unread'] and not new['unread']:
                if not any((new['marked_read_on'], new['marked_read_by'])):
                    error = 'Missing marked_read_by or marked_read_on fields'
                    self.raise_invalid(name='unread', description=error)

            # Device info is ignored if already read
            if not old['unread']:
                new['marked_read_on'] = old['marked_read_on']
                new['marked_read_by'] = old['marked_read_by']

        # Waiting for V2 to fetch articles
        if new['resolved_title'] is None:
            new['resolved_title'] = new['title']
        if new['resolved_url'] is None:
            new['resolved_url'] = new['url']

        # Reset info when article is marked as unreadd
        if new['unread']:
            new['marked_read_on'] = None
            new['marked_read_by'] = None
            new['read_position'] = 0

        return new

    def collection_post(self, *args, **kwargs):
        try:
            return super(Article, self).collection_post(*args, **kwargs)
        except httpexceptions.HTTPConflict as e:
            self.request.response.status_code = 200
            return e.existing
