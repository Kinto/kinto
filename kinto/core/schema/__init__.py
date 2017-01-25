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


# Objects

class ErrorSchema(colander.MappingSchema):
    """Body schema for Kinto errors."""

    code = colander.SchemaNode(colander.Integer())
    errno = colander.SchemaNode(colander.Integer())
    error = colander.SchemaNode(colander.String())
    message = colander.SchemaNode(colander.String(), missing=colander.drop)
    info = colander.SchemaNode(colander.String(), missing=colander.drop)
    details = colander.SchemaNode(Any(), missing=colander.drop)


class ResourceSchema(colander.MappingSchema):
    """Base resource schema, with *Cliquet* specific built-in options."""

    class Options:
        """
        Resource schema options.

        This is meant to be overriden for changing values:

        .. code-block:: python

            class Product(ResourceSchema):
                reference = colander.SchemaNode(colander.String())

                class Options:
                    readonly_fields = ('reference',)
        """
        readonly_fields = tuple()
        """Fields that cannot be updated. Values for fields will have to be
        provided either during record creation, through default values using
        ``missing`` attribute or implementing a custom logic in
        :meth:`kinto.core.resource.UserResource.process_record`.
        """

        preserve_unknown = True
        """Define if unknown fields should be preserved or not.

        The resource is schema-less by default. In other words, any field name
        will be accepted on records. Set this to ``False`` in order to limit
        the accepted fields to the ones defined in the schema.
        """

    @classmethod
    def get_option(cls, attr):
        default_value = getattr(ResourceSchema.Options, attr)
        return getattr(cls.Options, attr,  default_value)

    @classmethod
    def is_readonly(cls, field):
        """Return True if specified field name is read-only.

        :param str field: the field name in the schema
        :returns: ``True`` if the specified field is read-only,
            ``False`` otherwise.
        :rtype: bool
        """
        return field in cls.get_option("readonly_fields")

    def schema_type(self):
        if self.get_option("preserve_unknown") is True:
            unknown = 'preserve'
        else:
            unknown = 'ignore'
        return colander.Mapping(unknown=unknown)


class PermissionsSchema(colander.SchemaNode):
    """A permission mapping defines ACEs.

    It has permission names as keys and principals as values.

    ::

        {
            "write": ["fxa:af3e077eb9f5444a949ad65aa86e82ff"],
            "groups:create": ["fxa:70a9335eecfe440fa445ba752a750f3d"]
        }

    """
    def __init__(self, *args, **kwargs):
        self.known_perms = kwargs.pop('permissions', tuple())
        super(PermissionsSchema, self).__init__(*args, **kwargs)
        for perm in self.known_perms:
            self[perm] = self._get_node_principals(perm)

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='preserve')

    def deserialize(self, cstruct=colander.null):
        # Start by deserializing a simple mapping.
        permissions = super(PermissionsSchema, self).deserialize(cstruct)

        # In case it is optional in parent schema.
        if permissions in (colander.null, colander.drop):
            return permissions

        # Remove potential extra children from previous deserialization.
        self.children = []
        for perm in permissions.keys():
            # If know permissions is limited, then validate inline.
            if self.known_perms:
                colander.OneOf(choices=self.known_perms)(self, perm)

        # End up by deserializing a mapping whose keys are now known.
        return super(PermissionsSchema, self).deserialize(permissions)

    def _get_node_principals(self, perm):
        principal = colander.SchemaNode(colander.String(),
                                        missing=colander.drop)
        return colander.SchemaNode(colander.Sequence(), principal, name=perm,
                                   missing=colander.drop)


class JsonPatchOperationSchema(colander.MappingSchema):
    """Single JSON Patch Operation."""

    def op_validator():
        op_values = ['test', 'add', 'remove', 'replace', 'move', 'copy']
        return colander.OneOf(op_values)

    def path_validator():
        return colander.Regex('(/\w*)+')

    op = colander.SchemaNode(colander.String(), validator=op_validator())
    path = colander.SchemaNode(colander.String(), validator=path_validator())
    from_ = colander.SchemaNode(colander.String(), name='from',
                                validator=path_validator(), missing=colander.drop)
    value = colander.SchemaNode(Any(), missing=colander.drop)

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='raise')


