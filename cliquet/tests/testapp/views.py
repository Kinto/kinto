from cliquet.resource import BaseResource, ResourceSchema, register
import colander


class MushroomSchema(ResourceSchema):
    name = colander.SchemaNode(colander.String())


@register()
class Mushroom(BaseResource):
    mapping = MushroomSchema()
