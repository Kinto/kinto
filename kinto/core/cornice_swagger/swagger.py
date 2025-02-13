"""Cornice Swagger 2.0 documentor"""

import inspect
import warnings
from collections import OrderedDict

import colander
from pyramid.threadlocal import get_current_registry

from kinto.core.cornice import Service
from kinto.core.cornice.util import to_list
from kinto.core.cornice_swagger.converters import (
    ParameterConversionDispatcher as ParameterConverter,
)
from kinto.core.cornice_swagger.converters import TypeConversionDispatcher as TypeConverter
from kinto.core.cornice_swagger.util import body_schema_transformer, merge_dicts, trim


class CorniceSwaggerException(Exception):
    """Raised when cornice services have structural problems to be converted."""


class DefinitionHandler(object):
    """Handles Swagger object definitions provided by cornice as colander schemas."""

    json_pointer = "#/definitions/"

    def __init__(self, ref=0, type_converter=TypeConverter()):
        """
        :param ref:
            The depth that should be used by self.ref when calling self.from_schema.
        """

        self.definition_registry = {}
        self.ref = ref
        self.type_converter = type_converter

    def from_schema(self, schema_node, base_name=None):
        """
        Creates a Swagger definition from a colander schema.

        :param schema_node:
            Colander schema to be transformed into a Swagger definition.
        :param base_name:
            Schema alternative title.

        :rtype: dict
        :returns: Swagger schema.
        """
        return self._ref_recursive(self.type_converter(schema_node), self.ref, base_name)

    def _ref_recursive(self, schema, depth, base_name=None):
        """
        Dismantle nested swagger schemas into several definitions using JSON pointers.
        Note: This can be dangerous since definition titles must be unique.

        :param schema:
            Base swagger schema.
        :param depth:
            How many levels of the swagger object schemas should be split into
            swaggger definitions with JSON pointers. Default (0) is no split.
            You may use negative values to split everything.
        :param base_name:
            If schema doesn't have a name, the caller may provide it to be
            used as reference.

        :rtype: dict
        :returns:
            JSON pointer to the root definition schema,
            or the original definition if depth is zero.
        """

        if depth == 0:
            return schema

        if schema["type"] != "object":
            return schema

        name = base_name or schema["title"]

        pointer = self.json_pointer + name
        for child_name, child in schema.get("properties", {}).items():
            schema["properties"][child_name] = self._ref_recursive(child, depth - 1)

        self.definition_registry[name] = schema

        return {"$ref": pointer}


class ParameterHandler(object):
    """Handles swagger parameter definitions."""

    json_pointer = "#/parameters/"

    def __init__(
        self,
        definition_handler=DefinitionHandler(),
        ref=False,
        type_converter=TypeConverter(),
        parameter_converter=ParameterConverter(TypeConverter()),
    ):
        """
        :param definition_handler:
            Callable that handles swagger definition schemas.
        :param ref:
            Specifies the ref value when calling from_xxx methods.
        """

        self.parameter_registry = {}

        self.type_converter = type_converter
        self.parameter_converter = parameter_converter
        self.definitions = definition_handler
        self.ref = ref

    def from_schema(self, schema_node):
        """
        Creates a list of Swagger params from a colander request schema.

        :param schema_node:
            Request schema to be transformed into Swagger.
        :param validators:
            Validators used in colander with the schema.

        :rtype: list
        :returns: List of Swagger parameters.
        """

        params = []

        for param_schema in schema_node.children:
            location = param_schema.name
            if location == "body":
                name = param_schema.__class__.__name__
                if name == "body":
                    name = schema_node.__class__.__name__ + "Body"
                param = self.parameter_converter(location, param_schema)
                param["name"] = name
                if self.ref:
                    param = self._ref(param)
                params.append(param)

            elif location in (("path", "header", "headers", "querystring", "GET")):
                for node_schema in param_schema.children:
                    param = self.parameter_converter(location, node_schema)
                    if self.ref:
                        param = self._ref(param)
                    params.append(param)

        return params

    def from_path(self, path):
        """
        Create a list of Swagger path params from a cornice service path.

        :type path: string
        :rtype: list
        """
        path_components = path.split("/")
        param_names = [
            comp[1:-1] for comp in path_components if comp.startswith("{") and comp.endswith("}")
        ]

        params = []
        for name in param_names:
            param_schema = colander.SchemaNode(colander.String(), name=name)
            param = self.parameter_converter("path", param_schema)
            if self.ref:
                param = self._ref(param)
            params.append(param)

        return params

    def _ref(self, param, base_name=None):
        """
        Store a parameter schema and return a reference to it.

        :param schema:
            Swagger parameter definition.
        :param base_name:
            Name that should be used for the reference.

        :rtype: dict
        :returns: JSON pointer to the original parameter definition.
        """

        name = base_name or param.get("title", "") or param.get("name", "")

        pointer = self.json_pointer + name
        self.parameter_registry[name] = param

        return {"$ref": pointer}


class ResponseHandler(object):
    """Handles swagger response definitions."""

    json_pointer = "#/responses/"

    def __init__(
        self, definition_handler=DefinitionHandler(), type_converter=TypeConverter(), ref=False
    ):
        """
        :param definition_handler:
            Callable that handles swagger definition schemas.
        :param ref:
            Specifies the ref value when calling from_xxx methods.
        """

        self.response_registry = {}

        self.type_converter = type_converter
        self.definitions = definition_handler
        self.ref = ref

    def from_schema_mapping(self, schema_mapping):
        """
        Creates a Swagger response object from a dict of response schemas.

        :param schema_mapping:
            Dict with entries matching ``{status_code: response_schema}``.
        :rtype: dict
        :returns: Response schema.
        """

        responses = {}

        for status, response_schema in schema_mapping.items():
            response = {}
            if response_schema.description:
                response["description"] = response_schema.description
            else:
                raise CorniceSwaggerException("Responses must have a description.")

            for field_schema in response_schema.children:
                location = field_schema.name

                if location == "body":
                    title = field_schema.__class__.__name__
                    if title == "body":
                        title = response_schema.__class__.__name__ + "Body"
                    field_schema.title = title
                    response["schema"] = self.definitions.from_schema(field_schema)

                elif location in ("header", "headers"):
                    header_schema = self.type_converter(field_schema)
                    headers = header_schema.get("properties")
                    if headers:
                        # Response headers doesn't accept titles
                        for header in headers.values():
                            header.pop("title")

                        response["headers"] = headers

            pointer = response_schema.__class__.__name__
            if self.ref:
                response = self._ref(response, pointer)
            responses[status] = response

        return responses

    def _ref(self, resp, base_name=None):
        """
        Store a response schema and return a reference to it.

        :param schema:
            Swagger response definition.
        :param base_name:
            Name that should be used for the reference.

        :rtype: dict
        :returns: JSON pointer to the original response definition.
        """

        name = base_name or resp.get("title", "") or resp.get("name", "")

        pointer = self.json_pointer + name
        self.response_registry[name] = resp

        return {"$ref": pointer}


class CorniceSwagger(object):
    """Handles the creation of a swagger document from a cornice application."""

    services = []
    """List of cornice services to document. You may use
    `cornice.service.get_services()` to get it."""

    definitions = DefinitionHandler
    """Default :class:`cornice_swagger.swagger.DefinitionHandler` class to use when
    handling OpenAPI schema definitions from kinto.core.cornice payload schemas."""

    parameters = ParameterHandler
    """Default :class:`cornice_swagger.swagger.ParameterHandler` class to use when
    handling OpenAPI operation parameters from kinto.core.cornice request schemas."""

    responses = ResponseHandler
    """Default :class:`cornice_swagger.swagger.ResponseHandler` class to use when
    handling OpenAPI responses from kinto.core.cornice_swagger defined responses."""

    schema_transformers = [body_schema_transformer]
    """List of request schema transformers that should be applied to a request
    schema to make it comply with a cornice default request schema."""

    type_converter = TypeConverter
    """Default :class:`cornice_swagger.converters.schema.TypeConversionDispatcher`
    class used for converting colander schema Types to Swagger Types."""

    parameter_converter = ParameterConverter
    """Default :class:`cornice_swagger.converters.parameters.ParameterConversionDispatcher`
    class used for converting colander/cornice request schemas to Swagger Parameters."""

    custom_type_converters = {}
    """Mapping for supporting custom types conversion on the default TypeConverter.
    Should map `colander.TypeSchema` to `cornice_swagger.converters.schema.TypeConverter`
    callables."""

    default_type_converter = None
    """Supplies a default type converter matching the interface of
    `cornice_swagger.converters.schema.TypeConverter` to be used with unknown types."""

    default_tags = None
    """Provide a default list of tags or a callable that takes a cornice
    service and the method name (e.g GET) and returns a list of Swagger
    tags to be used if not provided by the view."""

    default_op_ids = None
    """Provide a callable that takes a cornice service and the method name
    (e.g. GET) and returns an operation Id that is used if an operation Id is
    not provided. Each operation Id should be unique."""

    default_security = None
    """Provide a default list or a callable that takes a cornice service and
    the method name (e.g. GET) and returns a list of OpenAPI security policies."""

    summary_docstrings = False
    """Enable extracting operation summaries from view docstrings."""

    ignore_methods = ["HEAD", "OPTIONS"]
    """List of service methods that should NOT be presented on the
    documentation. You may use this to remove methods that are not
    essential on the API documentation. Default ignores HEAD and OPTIONS."""

    ignore_ctypes = []
    """List of service content-types that should NOT be presented on the
    documentation. You may use this when a Cornice service definition has
    multiple view definitions for a same method, which is not supported on
    OpenAPI 2.0."""

    api_title = ""
    """Title of the OpenAPI document."""

    api_version = ""
    """Version of the OpenAPI document."""

    base_path = "/"
    """Base path of the documented API. Default is "/"."""

    swagger = {"info": {}}
    """Base OpenAPI document that should be merged with the extracted info
    from the generate call."""

    def __init__(
        self,
        services=None,
        def_ref_depth=0,
        param_ref=False,
        resp_ref=False,
        pyramid_registry=None,
    ):
        """
        :param services:
            List of cornice services to document. You may use
            cornice.service.get_services() to get it.
        :param def_ref_depth:
            How depth swagger object schemas should be split into
            swaggger definitions with JSON pointers. Default (0) is no split.
            You may use negative values to split everything.
        :param param_ref:
            Defines if swagger parameters should be put inline on the operation
            or on the parameters section and referenced by JSON pointers.
            Default is inline.
        :param resp_ref:
            Defines if swagger responses should be put inline on the operation
            or on the responses section and referenced by JSON pointers.
            Default is inline.
        :param pyramid_registry:
            Pyramid registry, should be passed if you use pyramid routes
            instead of service level paths.
        """
        super(CorniceSwagger, self).__init__()

        type_converter = self.type_converter(
            self.custom_type_converters, self.default_type_converter
        )
        parameter_converter = self.parameter_converter(type_converter)
        self.pyramid_registry = pyramid_registry
        if services is not None:
            self.services = services

        # Instantiate handlers
        self.definitions = self.definitions(ref=def_ref_depth, type_converter=type_converter)
        self.parameters = self.parameters(
            self.definitions,
            ref=param_ref,
            type_converter=type_converter,
            parameter_converter=parameter_converter,
        )
        self.responses = self.responses(
            self.definitions, ref=resp_ref, type_converter=type_converter
        )

    def generate(
        self, title=None, version=None, base_path=None, info=None, swagger=None, **kwargs
    ):
        """Generate a Swagger 2.0 documentation. Keyword arguments may be used
        to provide additional information to build methods as such ignores.

        :param title:
            The name presented on the swagger document.
        :param version:
            The version of the API presented on the swagger document.
        :param base_path:
            The path that all requests to the API must refer to.
        :param info:
            Swagger info field.
        :param swagger:
            Extra fields that should be provided on the swagger documentation.

        :rtype: dict
        :returns: Full OpenAPI/Swagger compliant specification for the application.
        """
        title = title or self.api_title
        version = version or self.api_version
        info = info or self.swagger.get("info", {})
        swagger = swagger or self.swagger
        base_path = base_path or self.base_path

        swagger = swagger.copy()
        info.update(title=title, version=version)
        swagger.update(swagger="2.0", info=info, basePath=base_path)

        paths, tags = self._build_paths()

        # Update the provided tags with the extracted ones preserving order
        if tags:
            swagger.setdefault("tags", [])
            tag_names = {t["name"] for t in swagger["tags"]}
            for tag in tags:
                if tag["name"] not in tag_names:
                    swagger["tags"].append(tag)

        # Create/Update swagger sections with extracted values where not provided
        if paths:
            swagger.setdefault("paths", {})
            merge_dicts(swagger["paths"], paths)

        definitions = self.definitions.definition_registry
        if definitions:
            swagger.setdefault("definitions", {})
            merge_dicts(swagger["definitions"], definitions)

        parameters = self.parameters.parameter_registry
        if parameters:
            swagger.setdefault("parameters", {})
            merge_dicts(swagger["parameters"], parameters)

        responses = self.responses.response_registry
        if responses:
            swagger.setdefault("responses", {})
            merge_dicts(swagger["responses"], responses)

        return swagger

    def __call__(self, *args, **kwargs):
        """Deprecated alias of `generate`."""
        self.__dict__.update(**kwargs)

        message = "Calling `CorniceSwagger is deprecated, call `generate` instead"
        warnings.warn(message, DeprecationWarning)
        return self.generate(*args, **kwargs)

    def _check_tags(self, tags):
        """Check if tags was correctly defined as a list"""
        if not isinstance(tags, list):
            raise CorniceSwaggerException("tags should be a list or callable")

    def _get_tags(self, current_tags, new_tags):
        tags = list(current_tags)
        for tag in new_tags:
            root_tag = {"name": tag}
            if root_tag not in tags:
                tags.append(root_tag)
        return tags

    def _build_paths(self):
        """
        Build the Swagger "paths" and "tags" attributes from kinto.core.cornice service
        definitions.
        """
        paths = {}
        tags = []

        for service in self.services:
            path, path_obj = self._extract_path_from_service(service)

            service_tags = getattr(service, "tags", [])
            self._check_tags(service_tags)
            tags = self._get_tags(tags, service_tags)

            for method, view, args in service.definitions:
                if method.lower() in map(str.lower, self.ignore_methods):
                    continue

                op = self._extract_operation_from_view(view, args)

                if any(ctype in op.get("consumes", []) for ctype in self.ignore_ctypes):
                    continue

                # XXX: Swagger doesn't support different schemas for for a same method
                # with different ctypes as cornice. If this happens, you may ignore one
                # content-type from the documentation otherwise we raise an Exception
                # Related to https://github.com/OAI/OpenAPI-Specification/issues/146
                previous_definition = path_obj.get(method.lower())
                if previous_definition:
                    raise CorniceSwaggerException(
                        (
                            "Swagger doesn't support multiple "
                            "views for a same method. You may "
                            "ignore one."
                        )
                    )

                # If tag not defined and a default tag is provided
                if "tags" not in op and self.default_tags:
                    if callable(self.default_tags):
                        op["tags"] = self.default_tags(service, method)
                    else:
                        op["tags"] = self.default_tags

                op_tags = op.get("tags", [])
                self._check_tags(op_tags)

                # Add service tags
                if service_tags:
                    new_tags = service_tags + op_tags
                    op["tags"] = list(OrderedDict.fromkeys(new_tags))

                # Add method tags to root tags
                tags = self._get_tags(tags, op_tags)

                # If operation id is not defined and a default generator is provided
                if "operationId" not in op and self.default_op_ids:
                    if not callable(self.default_op_ids):
                        raise CorniceSwaggerException("default_op_id should be a callable.")
                    op["operationId"] = self.default_op_ids(service, method)

                # If security options not defined and default is provided
                if "security" not in op and self.default_security:
                    if callable(self.default_security):
                        op["security"] = self.default_security(service, method)
                    else:
                        op["security"] = self.default_security

                if not isinstance(op.get("security", []), list):
                    raise CorniceSwaggerException("security should be a list or callable")

                path_obj[method.lower()] = op
            paths[path] = path_obj

        return paths, tags

    def _extract_path_from_service(self, service):
        """
        Extract path object and its parameters from service definitions.

        :param service:
            Cornice service to extract information from.

        :rtype: dict
        :returns: Path definition.
        """

        path_obj = {}
        path = service.path
        route_name = getattr(service, "pyramid_route", None)
        # handle services that don't create fresh routes,
        # we still need the paths so we need to grab pyramid introspector to
        # extract that information
        if route_name:
            # avoid failure if someone forgets to pass registry
            registry = self.pyramid_registry or get_current_registry()
            route_intr = registry.introspector.get("routes", route_name)
            if route_intr:
                path = route_intr["pattern"]
            else:
                msg = "Route `{}` is not found by pyramid introspector".format(route_name)
                raise ValueError(msg)

        # handle traverse and subpath as regular parameters
        # docs.pylonsproject.org/projects/pyramid/en/latest/narr/hybrid.html
        for subpath_marker in ("*subpath", "*traverse"):
            path = path.replace(subpath_marker, "{subpath}")

        # Extract path parameters
        parameters = self.parameters.from_path(path)
        if parameters:
            path_obj["parameters"] = parameters

        return path, path_obj

    def _extract_operation_from_view(self, view, args):
        """
        Extract swagger operation details from colander view definitions.

        :param view:
            View to extract information from.
        :param args:
            Arguments from the view decorator.

        :rtype: dict
        :returns: Operation definition.
        """

        op = {
            "responses": {"default": {"description": "UNDOCUMENTED RESPONSE"}},
        }

        # If 'produces' are not defined in the view, try get from renderers
        renderer = args.get("renderer", "")

        is_json_renderer = (
            "json" in renderer  # allows for "json" or "simplejson"
            or renderer == Service.renderer  # default renderer is json.
        )

        if is_json_renderer:
            produces = ["application/json"]
        elif renderer == "xml":
            produces = ["text/xml"]
        else:
            produces = None

        if produces:
            op.setdefault("produces", produces)

        # Get explicit accepted content-types
        consumes = args.get("content_type")

        if consumes is not None:
            # convert to a list, if it's not yet one
            consumes = to_list(consumes)

            # It is possible to add callables for content_type, so we have to
            # to filter those out, since we cannot evaluate those here.
            consumes = [x for x in consumes if not callable(x)]
            op["consumes"] = consumes

        # Get parameters from view schema
        is_colander = self._is_colander_schema(args)
        if is_colander:
            schema = self._extract_transform_colander_schema(args)
            parameters = self.parameters.from_schema(schema)
        else:
            # Bail out for now
            parameters = None
        if parameters:
            op["parameters"] = parameters

        # Get summary from docstring
        if isinstance(view, str):
            if "klass" in args:
                ob = args["klass"]
                view_ = getattr(ob, view.lower())
                docstring = trim(view_.__doc__)
        else:
            docstring = str(trim(view.__doc__))

        if docstring and self.summary_docstrings:
            op["summary"] = docstring

        # Get response definitions
        if "response_schemas" in args:
            op["responses"] = self.responses.from_schema_mapping(args["response_schemas"])

        # Get response tags
        if "tags" in args:
            op["tags"] = args["tags"]

        # Get response operationId
        if "operation_id" in args:
            op["operationId"] = args["operation_id"]

        # Get security policies
        if "api_security" in args:
            op["security"] = args["api_security"]

        return op

    def _is_colander_schema(self, args):
        schema = args.get("schema")
        return isinstance(schema, colander.Schema) or (
            inspect.isclass(schema) and issubclass(schema, colander.MappingSchema)
        )

    def _extract_transform_colander_schema(self, args):
        """
        Extract schema from view args and transform it using
        the pipeline of schema transformers

        :param args:
            Arguments from the view decorator.

        :rtype: colander.MappingSchema()
        :returns: View schema cloned and transformed
        """

        schema = args.get("schema", colander.MappingSchema())
        if not isinstance(schema, colander.Schema):
            schema = schema()
        schema = schema.clone()
        for transformer in self.schema_transformers:
            schema = transformer(schema, args)
        return schema
