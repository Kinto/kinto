import colander

from kinto.core.schema import (QueryField, HeaderField, FieldList,
                               HeaderQuotedInteger, JsonPatchOperationSchema)
from kinto.core.utils import strip_whitespace, msec_time, decode_header, native_value


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


class JsonPatchRequestSchema(RecordRequestSchema):
    """Body used with JSON Patch (application/json-patch+json) as in RFC 6902."""

    body = colander.SequenceSchema(JsonPatchOperationSchema(missing=colander.drop),
                                   missing=colander.drop)
