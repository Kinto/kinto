"""
This module handles the conversion between colander object schemas and swagger
object schemas.
"""

from kinto.core.cornice_swagger.converters.parameters import ParameterConversionDispatcher
from kinto.core.cornice_swagger.converters.schema import TypeConversionDispatcher


def convert_schema(schema_node):
    dispatcher = TypeConversionDispatcher()
    converted = dispatcher(schema_node)

    return converted


def convert_parameter(location, schema_node, definition_handler=convert_schema):
    dispatcher = ParameterConversionDispatcher(definition_handler)
    converted = dispatcher(location, schema_node)

    return converted
