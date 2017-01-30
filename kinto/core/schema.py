import six
import colander

from kinto.core.utils import strip_whitespace, msec_time, decode_header, native_value


# Types

class Any(colander.SchemaType):
    """Colander type agnostic field."""

    def deserialize(self, node, cstruct=colander.null):
        if not cstruct or cstruct == colander.null:
            return colander.drop

        return cstruct


# Nodes

class TimeStamp(colander.SchemaNode):
    """Basic integer schema field that can be set to current server timestamp
    in milliseconds if no value is provided.

    .. code-block:: python

        class Book(ResourceSchema):
            added_on = TimeStamp()
            read_on = TimeStamp(auto_now=False, missing=-1)
    """
    schema_type = colander.Integer

    title = 'Epoch timestamp'
    """Default field title."""

    auto_now = True
    """Set to current server timestamp (*milliseconds*) if not provided."""

    missing = None
    """Default field value if not provided in record."""

    def deserialize(self, cstruct=colander.null):
        if cstruct is colander.null and self.auto_now:
            cstruct = msec_time()
        return super(TimeStamp, self).deserialize(cstruct)


class URL(colander.SchemaNode):
    """String field representing a URL, with max length of 2048.
    This is basically a shortcut for string field with
    `~colander:colander.url`.

    .. code-block:: python

        class BookmarkSchema(ResourceSchema):
            url = URL()
    """
    schema_type = colander.String
    validator = colander.All(colander.url, colander.Length(min=1, max=2048))

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)


class HeaderField(colander.SchemaNode):
    """Basic header field SchemaNode."""

    missing = colander.drop

    def deserialize(self, cstruct=colander.null):
        if isinstance(cstruct, six.binary_type):
            try:
                cstruct = decode_header(cstruct)
            except UnicodeDecodeError:
                raise colander.Invalid(self, msg='Headers should be UTF-8 encoded')
        return super(HeaderField, self).deserialize(cstruct)


class QueryField(colander.SchemaNode):
    """Basic querystring field SchemaNode."""

    missing = colander.drop

    def deserialize(self, cstruct=colander.null):
        if isinstance(cstruct, six.string_types):
            cstruct = native_value(cstruct)
        return super(QueryField, self).deserialize(cstruct)


class FieldList(QueryField):
    """String field representing a list of attributes."""

    schema_type = colander.Sequence
    error_message = "The value should be a list of comma separated attributes"
    missing = colander.drop
    fields = colander.SchemaNode(colander.String(), missing=colander.drop)

    def deserialize(self, cstruct=colander.null):
        if isinstance(cstruct, six.string_types):
            cstruct = cstruct.split(',')
        return super(FieldList, self).deserialize(cstruct)


class HeaderQuotedInteger(HeaderField):
    """Integer between "" used in precondition headers."""

    schema_type = colander.String
    error_message = "The value should be integer between double quotes"
    validator = colander.Any(colander.Regex('\*'),
                             colander.Regex('^"([0-9]+?)"$', msg=error_message))

    def deserialize(self, cstruct=colander.null):
        param = super(HeaderQuotedInteger, self).deserialize(cstruct)
        if param is colander.drop or param == '*':
            return param

        return int(param[1:-1])
