import warnings

import colander

from kinto.core.errors import ErrorSchema
from kinto.core.schema import (
    URL,
    Any,
    FieldList,
    HeaderField,
    HeaderQuotedInteger,
    QueryField,
    TimeStamp,
)
from kinto.core.utils import native_value

POSTGRESQL_MAX_INTEGER_VALUE = 2**63

positive_big_integer = colander.Range(min=0, max=POSTGRESQL_MAX_INTEGER_VALUE)


class TimeStamp(TimeStamp):
    """This schema is deprecated, you shoud use `kinto.core.schema.TimeStamp` instead."""

    def __init__(self, *args, **kwargs):
        message = (
            "`kinto.core.resource.schema.TimeStamp` is deprecated, "
            "use `kinto.core.schema.TimeStamp` instead."
        )
        warnings.warn(message, DeprecationWarning)
        super().__init__(*args, **kwargs)


class URL(URL):
    """This schema is deprecated, you shoud use `kinto.core.schema.URL` instead."""

    def __init__(self, *args, **kwargs):
        message = (
            "`kinto.core.resource.schema.URL` is deprecated, "
            "use `kinto.core.schema.URL` instead."
        )
        warnings.warn(message, DeprecationWarning)
        super().__init__(*args, **kwargs)


# Resource related schemas


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
        provided either during object creation, through default values using
        ``missing`` attribute or implementing a custom logic in
        :meth:`kinto.core.resource.Resource.process_object`.
        """

        preserve_unknown = True
        """Define if unknown fields should be preserved or not.

        The resource is schema-less by default. In other words, any field name
        will be accepted on objects. Set this to ``False`` in order to limit
        the accepted fields to the ones defined in the schema.
        """

    @classmethod
    def get_option(cls, attr):
        default_value = getattr(ResourceSchema.Options, attr)
        return getattr(cls.Options, attr, default_value)

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
            unknown = "preserve"
        else:
            unknown = "ignore"
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
        self.known_perms = kwargs.pop("permissions", tuple())
        super().__init__(*args, **kwargs)

        for perm in self.known_perms:
            self[perm] = self._get_node_principals(perm)

    def schema_type(self):
        if self.known_perms:
            return colander.Mapping(unknown="raise")
        else:
            return colander.Mapping(unknown="preserve")

    def deserialize(self, cstruct=colander.null):
        # If permissions are not a mapping (e.g null or invalid), try deserializing
        if not isinstance(cstruct, dict):
            return super().deserialize(cstruct)

        # If using application/merge-patch+json we need to allow null values as they
        # represent removing a key.
        cstruct, removed_keys = self._preprocess_null_perms(cstruct)

        # If permissions are listed, check fields and produce fancy error messages
        if self.known_perms:
            for perm in cstruct:
                colander.OneOf(choices=self.known_perms)(self, perm)
            permissions = super().deserialize(cstruct)

        # Else deserialize the fields that are not on the schema
        else:
            permissions = {}
            perm_schema = colander.SequenceSchema(colander.SchemaNode(colander.String()))
            for perm, principals in cstruct.items():
                permissions[perm] = perm_schema.deserialize(principals)

        return self._postprocess_null_perms(permissions, removed_keys)

    def _get_node_principals(self, perm):
        principal = colander.SchemaNode(colander.String())
        return colander.SchemaNode(
            colander.Sequence(), principal, name=perm, missing=colander.drop
        )

    @staticmethod
    def _preprocess_null_perms(cstruct):
        keys = {k for k, v in cstruct.items() if v is None}
        cleaned = {k: v for k, v in cstruct.items() if v is not None}
        return cleaned, keys

    @staticmethod
    def _postprocess_null_perms(validated, keys):
        validated.update({k: None for k in keys})
        return validated


# Header schemas


class HeaderSchema(colander.MappingSchema):
    """Base schema used for validating and deserializing request headers."""

    missing = colander.drop

    if_match = HeaderQuotedInteger(name="If-Match")
    if_none_match = HeaderQuotedInteger(name="If-None-Match")

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="preserve")


class PatchHeaderSchema(HeaderSchema):
    """Header schema used with PATCH requests."""

    def response_behavior_validator():
        return colander.OneOf(["full", "light", "diff"])

    response_behaviour = HeaderField(
        colander.String(), name="Response-Behavior", validator=response_behavior_validator()
    )


# Querystring schemas


class QuerySchema(colander.MappingSchema):
    """
    Schema used for validating and deserializing querystrings. It will include
    and try to guess the type of unknown fields (field filters) on deserialization.
    """

    missing = colander.drop

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="ignore")

    def deserialize(self, cstruct=colander.null):
        """
        Deserialize and validate the QuerySchema fields and try to deserialize and
        get the native value of additional filds (field filters) that may be present
        on the cstruct.

        e.g:: ?exclude_id=a,b&deleted=true -> {'exclude_id': ['a', 'b'], deleted: True}
        """
        values = {}

        schema_values = super().deserialize(cstruct)
        if schema_values is colander.drop:
            return schema_values

        # Deserialize querystring field filters (see docstring e.g)
        for k, v in cstruct.items():
            # Deserialize lists used on contains_ and contains_any_ filters
            if k.startswith("contains_"):
                as_list = native_value(v)

                if not isinstance(as_list, list):
                    values[k] = [as_list]
                else:
                    values[k] = as_list

            # Deserialize lists used on in_ and exclude_ filters
            elif k.startswith("in_") or k.startswith("exclude_"):
                as_list = FieldList().deserialize(v)
                values[k] = [native_value(v) for v in as_list]
            else:
                values[k] = native_value(v)

        values.update(schema_values)
        return values


class PluralQuerySchema(QuerySchema):
    """Querystring schema used with plural endpoints."""

    _limit = QueryField(colander.Integer(), validator=positive_big_integer)
    _sort = FieldList()
    _token = QueryField(colander.String())
    _since = QueryField(colander.Integer(), validator=positive_big_integer)
    _to = QueryField(colander.Integer(), validator=positive_big_integer)
    _before = QueryField(colander.Integer(), validator=positive_big_integer)
    id = QueryField(colander.String())
    last_modified = QueryField(colander.Integer(), validator=positive_big_integer)


class ObjectGetQuerySchema(QuerySchema):
    """Querystring schema for GET object requests."""

    _fields = FieldList()


class PluralGetQuerySchema(PluralQuerySchema):
    """Querystring schema for GET plural endpoints requests."""

    _fields = FieldList()


# Body Schemas


class ObjectSchema(colander.MappingSchema):
    @colander.deferred
    def data(node, kwargs):
        data = kwargs.get("data")
        if data:
            # Check if empty object is allowed.
            # (e.g every schema fields have defaults)
            try:
                data.deserialize({})
            except colander.Invalid:
                pass
            else:
                data.default = {}
                data.missing = colander.drop
        return data

    @colander.deferred
    def permissions(node, kwargs):
        def get_perms(node, kwargs):
            return kwargs.get("permissions")

        # Set if node is provided, else keep deferred. This allows binding the body
        # on Resource first and bind permissions later.
        # XXX: probably not necessary now that UserResource is gone.
        return get_perms(node, kwargs) or colander.deferred(get_perms)

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="raise")


class JsonPatchOperationSchema(colander.MappingSchema):
    """Single JSON Patch Operation."""

    def op_validator():
        op_values = ["test", "add", "remove", "replace", "move", "copy"]
        return colander.OneOf(op_values)

    def path_validator():
        return colander.Regex("(/\\w*)+")

    op = colander.SchemaNode(colander.String(), validator=op_validator())
    path = colander.SchemaNode(colander.String(), validator=path_validator())
    from_ = colander.SchemaNode(
        colander.String(), name="from", validator=path_validator(), missing=colander.drop
    )
    value = colander.SchemaNode(Any(), missing=colander.drop)

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="raise")


class JsonPatchBodySchema(colander.SequenceSchema):
    """Body used with JSON Patch (application/json-patch+json) as in RFC 6902."""

    operations = JsonPatchOperationSchema(missing=colander.drop)


# Request schemas


class RequestSchema(colander.MappingSchema):
    """Base schema for kinto requests."""

    @colander.deferred
    def header(node, kwargs):
        return kwargs.get("header")

    @colander.deferred
    def querystring(node, kwargs):
        return kwargs.get("querystring")

    def after_bind(self, node, kw):
        # Set default bindings
        if not self.get("header"):
            self["header"] = HeaderSchema()
        if not self.get("querystring"):
            self["querystring"] = QuerySchema()


class PayloadRequestSchema(RequestSchema):
    """Base schema for methods that use a JSON request body."""

    @colander.deferred
    def body(node, kwargs):
        def get_body(node, kwargs):
            return kwargs.get("body")

        # Set if node is provided, else keep deferred (and allow bindind later)
        return get_body(node, kwargs) or colander.deferred(get_body)


class JsonPatchRequestSchema(RequestSchema):
    """JSON Patch (application/json-patch+json) request schema."""

    body = JsonPatchBodySchema()
    querystring = QuerySchema()
    header = PatchHeaderSchema()


# Response schemas


class ResponseHeaderSchema(colander.MappingSchema):
    """Kinto API custom response headers."""

    etag = HeaderQuotedInteger(name="Etag")
    last_modified = colander.SchemaNode(colander.String(), name="Last-Modified")


class ErrorResponseSchema(colander.MappingSchema):
    """Response schema used on 4xx and 5xx errors."""

    body = ErrorSchema()


class NotModifiedResponseSchema(colander.MappingSchema):
    """Response schema used on 304 Not Modified responses."""

    header = ResponseHeaderSchema()


class ObjectResponseSchema(colander.MappingSchema):
    """Response schema used with sigle resource endpoints."""

    header = ResponseHeaderSchema()

    @colander.deferred
    def body(node, kwargs):
        return kwargs.get("object")


class PluralResponseSchema(colander.MappingSchema):
    """Response schema used with plural endpoints."""

    header = ResponseHeaderSchema()

    @colander.deferred
    def body(node, kwargs):
        resource = kwargs.get("object")["data"]
        datalist = colander.MappingSchema()
        datalist["data"] = colander.SequenceSchema(resource, missing=[])
        return datalist


class ResourceReponses:
    """Class that wraps and handles Resource responses."""

    default_schemas = {
        "400": ErrorResponseSchema(description="The request is invalid."),
        "401": ErrorResponseSchema(description="The request is missing authentication headers."),
        "403": ErrorResponseSchema(
            description=(
                "The user is not allowed to perform the operation, "
                "or the resource is not accessible."
            )
        ),
        "406": ErrorResponseSchema(
            description="The client doesn't accept supported responses Content-Type."
        ),
        "412": ErrorResponseSchema(
            description="Object was changed or deleted since value in `If-Match` header."
        ),
        "default": ErrorResponseSchema(description="Unexpected error."),
    }
    default_object_schemas = {"200": ObjectResponseSchema(description="Return the target object.")}
    default_plural_schemas = {
        "200": PluralResponseSchema(description="Return a list of matching objects.")
    }
    default_get_schemas = {
        "304": NotModifiedResponseSchema(
            description="Reponse has not changed since value in If-None-Match header"
        )
    }
    default_post_schemas = {
        "200": ObjectResponseSchema(description="Return an existing object."),
        "201": ObjectResponseSchema(description="Return a created object."),
        "415": ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type."
        ),
    }
    default_put_schemas = {
        "201": ObjectResponseSchema(description="Return created object."),
        "415": ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type."
        ),
    }
    default_patch_schemas = {
        "415": ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type."
        )
    }
    default_delete_schemas = {}
    object_get_schemas = {
        "404": ErrorResponseSchema(description="The object does not exist or was deleted.")
    }
    object_patch_schemas = {
        "404": ErrorResponseSchema(description="The object does not exist or was deleted.")
    }
    object_delete_schemas = {
        "404": ErrorResponseSchema(description="The object does not exist or was already deleted.")
    }

    def get_and_bind(self, endpoint_type, method, **kwargs):
        """Wrap resource colander response schemas for an endpoint and return a dict
        of status codes mapping cloned and binded responses."""

        responses = self.default_schemas.copy()
        type_responses = getattr(self, f"default_{endpoint_type}_schemas")
        responses.update(**type_responses)

        verb_responses = f"default_{method.lower()}_schemas"
        method_args = getattr(self, verb_responses, {})
        responses.update(**method_args)

        method_responses = f"{endpoint_type}_{method.lower()}_schemas"
        endpoint_args = getattr(self, method_responses, {})
        responses.update(**endpoint_args)

        # Bind and clone schemas into a new dict
        bound = {code: resp.bind(**kwargs) for code, resp in responses.items()}

        return bound
