import colander
from colander import SchemaNode, String

from cliquet.utils import strip_whitespace, msec_time


class TimeStamp(colander.SchemaNode):
    """Basic integer field that takes current timestamp if no value
    is provided.
    """
    schema_type = colander.Integer
    title = 'Epoch timestamp'
    auto_now = True
    missing = None

    def deserialize(self, cstruct=colander.null):
        if cstruct is colander.null and self.auto_now:
            cstruct = msec_time()
        return super(TimeStamp, self).deserialize(cstruct)


class URL(SchemaNode):
    """String representing a URL."""
    schema_type = String
    validator = colander.All(colander.url, colander.Length(min=1, max=2048))

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)


class ResourceSchema(colander.MappingSchema):
    """Base resource schema.

    It brings common fields and behaviour for all inherited schemas:

    * ``id``
    * ``last_modified``

    Override to add extra fields using the Colander API.

    .. code-block :: python

        class Movie(ResourceSchema):
            director = colander.SchemaNode(colander.String())
    """
    id = colander.SchemaNode(colander.String(), missing=colander.drop)
    last_modified = TimeStamp()

    class Options:
        """
        Resource schema options.

        This is meant to be overriden for changing values:

        .. code-block :: python

            class Bookmark(ResourceSchema):
                url = schema.URL()

                class Options:
                    unique_fields = ('url',)
        """
        readonly_fields = ('id', 'last_modified')
        """Fields that cannot be updated"""

        unique_fields = ('id', 'last_modified')
        """Fields that must have unique values for the user collection"""

        preserve_unknown = False
        """Define if unknown fields should be preserved or not"""

    def get_option(self, attr):
        default_value = getattr(ResourceSchema.Options, attr)
        return getattr(self.Options, attr,  default_value)

    def is_readonly(self, field):
        """Return True if specified field name is read-only.

        :param field: the field name in the schema
        :type field: string
        :returns: `True` if the specified field is read-only,
            `False` otherwise.
        :rtype: boolean
        """
        return field in self.get_option("readonly_fields")

    def schema_type(self, **kw):
        if self.get_option("preserve_unknown") is True:
            unknown = 'preserve'
        else:
            unknown = 'ignore'
        return colander.Mapping(unknown=unknown)
