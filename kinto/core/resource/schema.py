import colander

from kinto.core.schema import (Any, QueryField, HeaderField, FieldList,
                               TimeStamp, HeaderQuotedInteger)
from kinto.core.errors import ErrorSchema
from kinto.core.utils import native_value


# Object Schemas

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


class RecordSchema(colander.MappingSchema):
    data = ResourceSchema(missing=colander.drop)


class CollectionSchema(colander.MappingSchema):
    data = colander.SequenceSchema(ResourceSchema(missing=colander.drop))


# Request Schemas

class HeaderSchema(colander.MappingSchema):
    """Schema used for validating and deserializing request headers. """

    def response_behavior_validator():
        return colander.OneOf(['full', 'light', 'diff'])

    if_match = HeaderQuotedInteger(name='If-Match')
    if_none_match = HeaderQuotedInteger(name='If-None-Match')
    response_behaviour = HeaderField(colander.String(), name='Response-Behavior',
                                     validator=response_behavior_validator())

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='preserve')


class QuerySchema(colander.MappingSchema):
    """
    Schema used for validating and deserializing querystrings. It will include
    and try to guess the type of unknown fields (field filters) on deserialization.
    """

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='ignore')

    def deserialize(self, cstruct=colander.null):
        """
        Deserialize and validate the QuerySchema fields and try to deserialize and
        get the native value of additional filds (field filters) that may be present
        on the cstruct.

        e.g:: ?exclude_id=a,b&deleted=true -> {'exclude_id': ['a', 'b'], deleted: True}
        """
        values = {}

        schema_values = super(QuerySchema, self).deserialize(cstruct)
        if schema_values is colander.drop:
            return schema_values

        # Deserialize querystring field filters (see docstring e.g)
        for k, v in cstruct.items():
            # Deserialize lists used on in_ and exclude_ filters
            if k.startswith('in_') or k.startswith('exclude_'):
                as_list = FieldList().deserialize(v)
                if isinstance(as_list, list):
                    values[k] = [native_value(v) for v in as_list]
            else:
                values[k] = native_value(v)

        values.update(schema_values)
        return values


class RecordQuerySchema(QuerySchema):

    _fields = FieldList()


class CollectionQuerySchema(QuerySchema):

    _fields = FieldList()
    _limit = QueryField(colander.Integer())
    _sort = FieldList()
    _token = QueryField(colander.String())
    _since = QueryField(colander.Integer())
    _to = QueryField(colander.Integer())
    _before = QueryField(colander.Integer())
    last_modified = QueryField(colander.Integer())


class RequestSchema(colander.MappingSchema):
    """Baseline schema for kinto requests."""

    header = HeaderSchema(missing=colander.drop)
    querystring = QuerySchema(missing=colander.drop)


class RecordRequestSchema(RequestSchema):
    querystring = RecordQuerySchema(missing=colander.drop)


class CollectionRequestSchema(RequestSchema):
    querystring = CollectionQuerySchema(missing=colander.drop)


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


class JsonPatchRequestSchema(RecordRequestSchema):
    """Body used with JSON Patch (application/json-patch+json) as in RFC 6902."""

    body = colander.SequenceSchema(JsonPatchOperationSchema(missing=colander.drop),
                                   missing=colander.drop)


# Response schemas

class ResponseHeaderSchema(colander.MappingSchema):
    etag = HeaderQuotedInteger(name='Etag')
    last_modified = colander.SchemaNode(colander.String(), name='Last-Modified')


class ErrorResponseSchema(colander.MappingSchema):
    body = ErrorSchema()


class NotModifiedResponseSchema(colander.MappingSchema):
    header = ResponseHeaderSchema()


class RecordResponseSchema(colander.MappingSchema):
    header = ResponseHeaderSchema()
    body = RecordSchema()


class CollectionResponseSchema(colander.MappingSchema):
    header = ResponseHeaderSchema()
    body = CollectionSchema()


class ResourceReponses(object):

    default_schemas = {
        '400': ErrorResponseSchema(
            description="The request is invalid."),
        '406': ErrorResponseSchema(
            description="The client doesn't accept supported responses Content-Type."),
        '412': ErrorResponseSchema(
            description="Record was changed or deleted since value in `If-Match` header."),
        'default': ErrorResponseSchema(
            description="Unexpected error."),

    }
    default_record_schemas = {
        '200': RecordResponseSchema(
            description="Return the target object.")
    }
    default_collection_schemas = {
        '200': CollectionResponseSchema(
            description="Return a list of matching objects.")
    }
    default_get_schemas = {
        '304': NotModifiedResponseSchema(
            description="Reponse has not changed since value in If-None-Match header")
    }
    default_post_schemas = {
        '200': RecordResponseSchema(
            description="Return an existing object."),
        '201': RecordResponseSchema(
            description="Return a created object."),
        '415': ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type.")
    }
    default_put_schemas = {
        '201': RecordResponseSchema(
            description="Return created object."),
        '415': ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type.")
    }
    default_patch_schemas = {
        '415': ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type.")
    }
    default_delete_schemas = {
    }
    record_get_schemas = {
        '404': ErrorResponseSchema(
            description="The object does not exist or was deleted."),
    }
    record_patch_schemas = {
        '404': ErrorResponseSchema(
            description="The object does not exist or was deleted."),
    }
    record_delete_schemas = {
        '404': ErrorResponseSchema(
            description="The object does not exist or was already deleted."),
    }

    def update_record_schema(self, responses, schema):

        schema = schema.clone()
        schema['data']['last_modified'] = TimeStamp()

        for response in responses.values():
            body = response.get('body')

            # Update record schema
            if isinstance(body, RecordSchema):
                response['body'] = schema

            # Update collection schema
            elif isinstance(body, CollectionSchema):
                if 'permissions' in schema:
                    schema.__delitem__('permissions')
                response['body']['data'] = colander.SequenceSchema(schema['data'])

    def get(self, endpoint_type, method, schema=None):

        responses = self.default_schemas.copy()
        type_responses = getattr(self, 'default_%s_schemas' % endpoint_type)
        responses.update(**type_responses)

        verb_responses = 'default_%s_schemas' % method.lower()
        method_args = getattr(self, verb_responses, {})
        responses.update(**method_args)

        method_responses = '%s_%s_schemas' % (endpoint_type, method.lower())
        endpoint_args = getattr(self, method_responses, {})
        responses.update(**endpoint_args)

        if schema:
            self.update_record_schema(responses, schema)

        return responses


class ShareableResourseResponses(ResourceReponses):

    def __init__(self):
        super(ShareableResourseResponses, self).__init__()
        self.default_schemas.update({
            '401': ErrorResponseSchema(
                description="The request is missing authentication headers."),
            '403': ErrorResponseSchema(
                description=("The user is not allowed to perform the operation, "
                             "or the resource is not accessible.")),
        })
