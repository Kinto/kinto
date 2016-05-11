import colander
from colander import SchemaNode, String

from cliquet.utils import strip_whitespace, msec_time


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
                    unique_fields = ('reference',)
        """
        unique_fields = tuple()
        """Fields that must have unique values for the user collection.
        During records creation and modification, a conflict error will be
        raised if unicity is about to be violated.
        """

        readonly_fields = tuple()
        """Fields that cannot be updated. Values for fields will have to be
        provided either during record creation, through default values using
        ``missing`` attribute or implementing a custom logic in
        :meth:`cliquet.resource.UserResource.process_record`.
        """

        preserve_unknown = False
        """Define if unknown fields should be preserved or not.

        For example, in order to define a schema-less resource, in other words
        a resource that will accept any form of record, the following schema
        definition is enough:

        .. code-block:: python

            class SchemaLess(ResourceSchema):
                class Options:
                    preserve_unknown = True
        """
    def get_option(self, attr):
        default_value = getattr(ResourceSchema.Options, attr)
        return getattr(self.Options, attr,  default_value)

    def is_readonly(self, field):
        """Return True if specified field name is read-only.

        :param str field: the field name in the schema
        :returns: ``True`` if the specified field is read-only,
            ``False`` otherwise.
        :rtype: bool
        """
        return field in self.get_option("readonly_fields")

    def schema_type(self, **kw):
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

    def schema_type(self, **kw):
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

            # Add a String list child node with the name of ``perm``.
            self.add(self._get_node_principals(perm))

        # End up by deserializing a mapping whose keys are now known.
        return super(PermissionsSchema, self).deserialize(permissions)

    def _get_node_principals(self, perm):
        principal = colander.SchemaNode(colander.String())
        return colander.SchemaNode(colander.Sequence(), principal, name=perm)


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


class URL(SchemaNode):
    """String field representing a URL, with max length of 2048.
    This is basically a shortcut for string field with
    `~colander:colander.url`.

    .. code-block:: python

        class BookmarkSchema(ResourceSchema):
            url = URL()
    """
    schema_type = String
    validator = colander.All(colander.url, colander.Length(min=1, max=2048))

    def preparer(self, appstruct):
        return strip_whitespace(appstruct)
