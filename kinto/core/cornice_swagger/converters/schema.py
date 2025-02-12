"""
This module handles the conversion between colander object schemas and swagger
object schemas by converting types and node validators.
"""

import colander

from kinto.core.cornice_swagger.converters.exceptions import NoSuchConverter


def convert_length_validator_factory(max_key, min_key):
    def validator_converter(validator):
        converted = None

        if isinstance(validator, colander.Length):
            converted = {}
            if validator.max is not None:
                converted[max_key] = validator.max
            if validator.min is not None:
                converted[min_key] = validator.min

        return converted

    return validator_converter


def convert_oneof_validator_factory():
    def validator_converter(validator):
        converted = None

        if isinstance(validator, colander.OneOf):
            converted = {"enum": list(validator.choices)}
        return converted

    return validator_converter


def convert_range_validator(validator):
    converted = None

    if isinstance(validator, colander.Range):
        converted = {}

        if validator.max is not None:
            converted["maximum"] = validator.max
        if validator.min is not None:
            converted["minimum"] = validator.min

    return converted


def convert_regex_validator(validator):
    converted = None

    if isinstance(validator, colander.Regex):
        converted = {}

        if hasattr(colander, "url") and validator is colander.url:
            converted["format"] = "url"
        elif isinstance(validator, colander.Email):
            converted["format"] = "email"
        else:
            converted["pattern"] = validator.match_object.pattern

    return converted


class ValidatorConversionDispatcher(object):
    def __init__(self, *converters):
        self.converters = converters

    def __call__(self, schema_node, validator=None):
        if validator is None:
            validator = schema_node.validator

        converted = {}
        if validator is not None:
            for converter in (self.convert_all_validator,) + self.converters:
                ret = converter(validator)
                if ret is not None:
                    converted = ret
                    break

        return converted

    def convert_all_validator(self, validator):
        if isinstance(validator, colander.All):
            converted = {}
            for v in validator.validators:
                ret = self(None, v)
                converted.update(ret)
            return converted
        else:
            return None


class TypeConverter(object):
    type = ""

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def convert_validator(self, schema_node):
        return {}

    def convert_type(self, schema_node):
        converted = {"type": self.type}

        if schema_node.title:
            converted["title"] = schema_node.title
        if schema_node.description:
            converted["description"] = schema_node.description
        if schema_node.missing not in (colander.required, colander.drop, colander.null):
            converted["default"] = schema_node.missing
        if "example" in schema_node.__dict__:
            converted["example"] = schema_node.example

        return converted

    def __call__(self, schema_node):
        converted = self.convert_type(schema_node)
        converted.update(self.convert_validator(schema_node))

        return converted


class BaseStringTypeConverter(TypeConverter):
    type = "string"
    format = None

    def convert_type(self, schema_node):
        converted = super(BaseStringTypeConverter, self).convert_type(schema_node)

        if self.format is not None:
            converted["format"] = self.format

        return converted


class BooleanTypeConverter(TypeConverter):
    type = "boolean"


class DateTypeConverter(BaseStringTypeConverter):
    format = "date"


class DateTimeTypeConverter(BaseStringTypeConverter):
    format = "date-time"


class NumberTypeConverter(TypeConverter):
    type = "number"

    convert_validator = ValidatorConversionDispatcher(
        convert_range_validator,
        convert_oneof_validator_factory(),
    )


class IntegerTypeConverter(NumberTypeConverter):
    type = "integer"


class StringTypeConverter(BaseStringTypeConverter):
    convert_validator = ValidatorConversionDispatcher(
        convert_length_validator_factory("maxLength", "minLength"),
        convert_regex_validator,
        convert_oneof_validator_factory(),
    )


class TimeTypeConverter(BaseStringTypeConverter):
    format = "time"


class ObjectTypeConverter(TypeConverter):
    type = "object"

    def convert_type(self, schema_node):
        converted = super(ObjectTypeConverter, self).convert_type(schema_node)

        properties = {}
        required = []

        for sub_node in schema_node.children:
            properties[sub_node.name] = self.dispatcher(sub_node)
            if sub_node.required:
                required.append(sub_node.name)

        if len(properties) > 0:
            converted["properties"] = properties

        if len(required) > 0:
            converted["required"] = required

        if schema_node.typ.unknown == "preserve":
            converted["additionalProperties"] = {}

        return converted


class ArrayTypeConverter(TypeConverter):
    type = "array"

    convert_validator = ValidatorConversionDispatcher(
        convert_length_validator_factory("maxItems", "minItems"),
    )

    def convert_type(self, schema_node):
        converted = super(ArrayTypeConverter, self).convert_type(schema_node)

        converted["items"] = self.dispatcher(schema_node.children[0])

        return converted


class TypeConversionDispatcher(object):
    def __init__(self, custom_converters={}, default_converter=None):
        self.converters = {
            colander.Boolean: BooleanTypeConverter,
            colander.Date: DateTypeConverter,
            colander.DateTime: DateTimeTypeConverter,
            colander.Float: NumberTypeConverter,
            colander.Integer: IntegerTypeConverter,
            colander.Mapping: ObjectTypeConverter,
            colander.Sequence: ArrayTypeConverter,
            colander.String: StringTypeConverter,
            colander.Time: TimeTypeConverter,
        }

        self.converters.update(custom_converters)
        self.default_converter = default_converter

    def __call__(self, schema_node):
        schema_type = schema_node.typ
        schema_type = type(schema_type)

        converter_class = self.converters.get(schema_type)
        if converter_class is None:
            if self.default_converter:
                converter_class = self.default_converter
            else:
                raise NoSuchConverter

        converter = converter_class(self)
        converted = converter(schema_node)

        return converted
