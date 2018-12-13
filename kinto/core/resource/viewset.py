import functools
import warnings

import colander
from cornice.validators import colander_validator
from pyramid.settings import asbool

from kinto.core import authorization

from .schema import (
    PermissionsSchema,
    RequestSchema,
    PayloadRequestSchema,
    PatchHeaderSchema,
    PluralQuerySchema,
    PluralGetQuerySchema,
    ObjectGetQuerySchema,
    ObjectSchema,
    ResourceReponses,
)


CONTENT_TYPES = ["application/json"]

PATCH_CONTENT_TYPES = ["application/merge-patch+json"]


class StrictSchema(colander.MappingSchema):
    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="raise")


class PartialSchema(colander.MappingSchema):
    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="ignore")


class SimpleSchema(colander.MappingSchema):
    @staticmethod
    def schema_type():
        return colander.Mapping(unknown="preserve")


class ViewSet:
    """The default ViewSet object.

    A viewset contains all the information needed to register
    any resource in the Cornice registry.

    It provides the same features as ``cornice.resource()``, except
    that it is much more flexible and extensible.
    """

    service_name = "{resource_name}-{endpoint_type}"
    plural_path = "/{resource_name}s"
    object_path = "/{resource_name}s/{{id}}"

    plural_methods = ("HEAD", "GET", "POST", "DELETE")
    object_methods = ("GET", "PUT", "PATCH", "DELETE")

    readonly_methods = ("GET", "OPTIONS", "HEAD")

    factory = authorization.RouteFactory

    responses = ResourceReponses()

    service_arguments = {"description": "Set of {resource_name}"}

    default_arguments = {
        "permission": authorization.DYNAMIC,
        "accept": CONTENT_TYPES,
        "schema": RequestSchema(),
    }

    default_post_arguments = {"content_type": CONTENT_TYPES, "schema": PayloadRequestSchema()}

    default_put_arguments = {"content_type": CONTENT_TYPES, "schema": PayloadRequestSchema()}

    default_patch_arguments = {
        "content_type": CONTENT_TYPES + PATCH_CONTENT_TYPES,
        "schema": PayloadRequestSchema().bind(header=PatchHeaderSchema()),
    }

    default_plural_arguments = {"schema": RequestSchema().bind(querystring=PluralQuerySchema())}
    plural_head_arguments = {
        "schema": RequestSchema().bind(querystring=PluralGetQuerySchema()),
        "cors_headers": (
            "Next-Page",
            "Last-Modified",
            "ETag",
            "Cache-Control",
            "Expires",
            "Pragma",
            "Total-Objects",
            "Total-Records",  # Deprecated.
        ),
    }
    plural_get_arguments = {
        "schema": RequestSchema().bind(querystring=PluralGetQuerySchema()),
        "cors_headers": (
            "Next-Page",
            "Last-Modified",
            "ETag",
            "Cache-Control",
            "Expires",
            "Pragma",
        ),
    }
    plural_post_arguments = {"schema": PayloadRequestSchema()}
    default_object_arguments = {}
    object_get_arguments = {
        "schema": RequestSchema().bind(querystring=ObjectGetQuerySchema()),
        "cors_headers": ("Last-Modified", "ETag", "Cache-Control", "Expires", "Pragma"),
    }

    def __init__(self, **kwargs):
        self.update(**kwargs)
        self.object_arguments = functools.partial(self.get_view_arguments, "object")
        self.plural_arguments = functools.partial(self.get_view_arguments, "plural")

    def update(self, **kwargs):
        """Update viewset attributes with provided values."""
        self.__dict__.update(**kwargs)

    def get_view_arguments(self, endpoint_type, resource_cls, method):
        """Return the Pyramid/Cornice view arguments for the given endpoint
        type and method.

        :param str endpoint_type: either "plural" or "object".
        :param resource_cls: the resource class.
        :param str method: the HTTP method.
        """
        args = {**self.default_arguments}
        default_arguments = getattr(self, f"default_{endpoint_type}_arguments")
        args.update(**default_arguments)

        by_http_verb = f"default_{method.lower()}_arguments"
        method_args = getattr(self, by_http_verb, {})
        args.update(**method_args)

        by_method = f"{endpoint_type}_{method.lower()}_arguments"
        endpoint_args = getattr(self, by_method, {})
        args.update(**endpoint_args)

        request_schema = args.get("schema", RequestSchema())
        object_schema = self.get_object_schema(resource_cls, method)
        request_schema = request_schema.bind(body=object_schema)
        response_schemas = self.responses.get_and_bind(endpoint_type, method, object=object_schema)

        args["schema"] = request_schema
        args["response_schemas"] = response_schemas

        validators = args.get("validators", [])
        validators.append(colander_validator)
        args["validators"] = validators

        return args

    def get_object_schema(self, resource_cls, method):
        """Return the Cornice schema for the given method.
        """
        if method.lower() in ("patch", "delete"):
            resource_schema = SimpleSchema
        else:
            resource_schema = resource_cls.schema

        permissions = PermissionsSchema(
            name="permissions", missing=colander.drop, permissions=resource_cls.permissions
        )

        object_schema = ObjectSchema().bind(data=resource_schema(), permissions=permissions)

        return object_schema

    def get_view(self, endpoint_type, method):
        """Return the view method name located on the resource object, for the
        given type and method.

        * For plural, this will be "plural_{method|lower}
        * For objects, this will be "{method|lower}.
        """
        if endpoint_type == "object":
            return method.lower()
        return f"{endpoint_type}_{method.lower()}"

    def get_name(self, resource_cls):
        """Returns the name of the resource.
        """
        # Provided on viewset during registration.
        if "name" in self.__dict__:
            return self.__dict__["name"]

        # Attribute on resource class (but not @property)
        has_class_attr = hasattr(resource_cls, "name") and not callable(resource_cls.name)
        if has_class_attr:
            return resource_cls.name

        # Use classname
        return resource_cls.__name__.lower()

    def get_service_name(self, endpoint_type, resource_cls):
        """Returns the name of the service, depending a given type and
        resource.
        """
        return self.service_name.format(
            resource_name=self.get_name(resource_cls), endpoint_type=endpoint_type
        )

    def get_service_arguments(self):
        return {**self.service_arguments, "factory": self.factory}

    def is_endpoint_enabled(self, endpoint_type, resource_name, method, settings):
        """Returns if the given endpoint is enabled or not.

        Uses the settings to tell so.
        """
        readonly_enabled = asbool(settings.get("readonly"))
        readonly_method = method.lower() in [m.lower() for m in self.readonly_methods]
        if readonly_enabled and not readonly_method:
            return False

        setting_enabled = f"{endpoint_type}_{resource_name}_{method.lower()}_enabled"
        return asbool(settings.get(setting_enabled, True))


class ShareableViewSet(ViewSet):
    def __init__(self, *args, **kwargs):
        message = "`ShareableViewSet` is deprecated, use `ViewSet` instead."
        warnings.warn(message, DeprecationWarning)
        super().__init__(*args, **kwargs)
