import colander

from kinto.core.cornice_swagger.converters.schema import TypeConverter


class MyNestedSchema(colander.MappingSchema):
    my_precious = colander.SchemaNode(colander.Boolean())


class BodySchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.String())
    timestamp = colander.SchemaNode(colander.Int())
    obj = MyNestedSchema()
    ex = colander.SchemaNode(colander.String(), missing=colander.drop, example="example string")


class QuerySchema(colander.MappingSchema):
    foo = colander.SchemaNode(
        colander.String(), validator=colander.Length(3), missing=colander.drop
    )


class HeaderSchema(colander.MappingSchema):
    bar = colander.SchemaNode(colander.String(), missing=colander.drop)


class PathSchema(colander.MappingSchema):
    meh = colander.SchemaNode(colander.String(), default="default")


class GetRequestSchema(colander.MappingSchema):
    querystring = QuerySchema()


class PutRequestSchema(colander.MappingSchema):
    body = BodySchema()
    querystring = QuerySchema()
    header = HeaderSchema()


class ResponseSchema(colander.MappingSchema):
    body = BodySchema()
    header = HeaderSchema()


response_schemas = {
    "200": ResponseSchema(description="Return ice cream"),
    "404": ResponseSchema(description="Return sadness"),
}


class DeclarativeSchema(colander.MappingSchema):
    @colander.instantiate(description="my body")
    class body(colander.MappingSchema):
        id = colander.SchemaNode(colander.String())


class AnotherDeclarativeSchema(colander.MappingSchema):
    @colander.instantiate(description="my another body")
    class body(colander.MappingSchema):
        timestamp = colander.SchemaNode(colander.Int())


class AnyType(colander.SchemaType):
    """A simple custom colander type."""

    def deserialize(self, cstruct=colander.null):
        return cstruct


class AnyTypeConverter(TypeConverter):
    def __call__(self, schema_node):
        return {}
