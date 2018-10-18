import colander
from jsonschema import Draft4Validator, ValidationError, SchemaError, RefResolutionError, validate
from pyramid.settings import asbool

from kinto.core import utils
from kinto.core.errors import raise_invalid
from kinto.views import object_exists_or_404


class JSONSchemaMapping(colander.SchemaNode):
    def schema_type(self, **kw):
        return colander.Mapping(unknown="preserve")

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
    required_fields = [f for f in schema.get("required", []) if f not in ignore_fields]
    # jsonschema doesn't accept 'required': [] yet.
    # See https://github.com/Julian/jsonschema/issues/337.
    # In the meantime, strip out 'required' if no other fields are required.
    if required_fields:
        schema = {**schema, "required": required_fields}
    else:
        schema = {f: v for f, v in schema.items() if f != "required"}

    data = {f: v for f, v in data.items() if f not in ignore_fields}

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
    # Raise an error here if a reference in the schema doesn't resolve.
    # jsonschema doesn't provide schema validation checking upon creation yet,
    # it must be validated against data.
    # See https://github.com/Julian/jsonschema/issues/399
    # For future support https://github.com/Julian/jsonschema/issues/346.
    except RefResolutionError as e:
        raise e


def validate_from_bucket_schema_or_400(data, resource_name, request, ignore_fields=[]):
    """Lookup in the parent objects if a schema was defined for this resource.

    If the schema validation feature is enabled, if a schema is/are defined, and if the
    data does not validate it/them, then it raises a 400 exception.
    """
    settings = request.registry.settings
    schema_validation = "experimental_collection_schema_validation"
    # If disabled from settings, do nothing.
    if not asbool(settings.get(schema_validation)):
        return

    bucket_id = request.matchdict["bucket_id"]
    bucket_uri = utils.instance_uri(request, "bucket", id=bucket_id)
    buckets = request.bound_data.setdefault("buckets", {})
    if bucket_uri not in buckets:
        # Unknown yet, fetch from storage.
        bucket = object_exists_or_404(
            request, collection_id="bucket", parent_id="", object_id=bucket_id
        )
        buckets[bucket_uri] = bucket

    # Let's see if the bucket defines a schema for this resource.
    metadata_field = "{}:schema".format(resource_name)
    bucket = buckets[bucket_uri]
    if metadata_field not in bucket:
        return

    # Validate or fail with 400.
    schema = bucket[metadata_field]
    try:
        validate_schema(data, schema, ignore_fields=ignore_fields)
    except ValidationError as e:
        raise_invalid(request, name=e.field, description=e.message)
    except RefResolutionError as e:
        raise_invalid(request, name="schema", description=str(e))
