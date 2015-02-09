import colander
from colander import SchemaNode, String

from readinglist.utils import strip_whitespace


class URL(SchemaNode):
    """String representing a URL."""
    schema_type = String
    validator = colander.All(colander.url, colander.Length(min=1, max=2048))

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)
