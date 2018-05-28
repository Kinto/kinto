import colander
from jsonschema import Draft4Validator, ValidationError, SchemaError, validate


class JSONSchemaMapping(colander.SchemaNode):
    def schema_type(self, **kw):
        return colander.Mapping(unknown='preserve')

    def deserialize(self, cstruct=colander.null):
        # Start by deserializing a simple mapping.
        validated = super().deserialize(cstruct)

        # In case it is optional in parent schema.
        if not validated or validated in (colander.null, colander.drop):
            return validated
        try:
            check_schema(validated)
        except ValidationError as e:
            self.raise_invalid(e.message)
        return validated


def check_schema(data):
    try:
        Draft4Validator.check_schema(data)
    except SchemaError as e:
        message = e.path.pop() + e.message
        raise ValidationError(message)


def validate_schema(data, schema, ignore_fields=[]):
    required_fields = [f for f in schema.get('required', []) if f not in ignore_fields]
    # jsonschema doesn't accept 'required': [] yet.
    # See https://github.com/Julian/jsonschema/issues/337.
    # In the meantime, strip out 'required' if no other fields are required.
    if required_fields:
        schema = {**schema, 'required': required_fields}
    else:
        schema = {f: v for f, v in schema.items() if f != 'required'}

    try:
        validate(data, schema)
    except ValidationError as e:
        if e.path:
            field = e.path[-1]
        elif e.validator_value:
            field = e.validator_value[-1]
        else:
            field = e.schema_path[-1]
        e.field = field
        raise e
