"""Converts from colander request chema to Swagger parameters."""

from kinto.core.cornice_swagger.converters.exceptions import NoSuchConverter


class ParameterConverter(object):
    _in = None

    def convert(self, schema_node, definition_handler):
        """
        Convert node schema into a parameter object.
        """

        converted = {"name": schema_node.name, "in": self._in, "required": schema_node.required}
        if schema_node.description:
            converted["description"] = schema_node.description

        if schema_node.default:
            converted["default"] = schema_node.default

        schema = definition_handler(schema_node)
        # Parameters shouldn't have a title
        schema.pop("title", None)
        converted.update(schema)

        if schema.get("type") == "array":
            converted["items"] = {"type": schema["items"]["type"]}

        return converted


class PathParameterConverter(ParameterConverter):
    _in = "path"

    def convert(self, schema_node, definition_handler):
        converted = super(PathParameterConverter, self).convert(schema_node, definition_handler)
        # Extract regex pattern from name
        template = converted["name"].split(":", 1)
        if len(template) == 2:
            converted["name"] = template[0]
            converted["pattern"] = template[1]

        return converted


class QueryParameterConverter(ParameterConverter):
    _in = "query"


class HeaderParameterConverter(ParameterConverter):
    _in = "header"


class BodyParameterConverter(ParameterConverter):
    _in = "body"

    def convert(self, schema_node, definition_handler):
        converted = {"name": schema_node.name, "in": self._in, "required": schema_node.required}
        if schema_node.description:
            converted["description"] = schema_node.description

        schema_node.title = schema_node.__class__.__name__
        schema = definition_handler(schema_node)
        converted["schema"] = schema

        return converted


class ParameterConversionDispatcher(object):
    converters = {
        "body": BodyParameterConverter,
        "path": PathParameterConverter,
        "querystring": QueryParameterConverter,
        "GET": QueryParameterConverter,
        "header": HeaderParameterConverter,
        "headers": HeaderParameterConverter,
    }

    def __init__(self, definition_handler):
        self.definition_handler = definition_handler

    def __call__(self, location, schema_node):
        converter_class = self.converters.get(location)
        if converter_class is None:
            raise NoSuchConverter()

        converter = converter_class()
        converted = converter.convert(schema_node, self.definition_handler)

        return converted
