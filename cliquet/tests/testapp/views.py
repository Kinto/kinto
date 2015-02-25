from cliquet.resource import BaseResource, ResourceSchema, crud
import colander


class MushroomSchema(ResourceSchema):
    name = colander.SchemaNode(colander.String())


@crud()
class Mushroom(BaseResource):
    mapping = MushroomSchema()
