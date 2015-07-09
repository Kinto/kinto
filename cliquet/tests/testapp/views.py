from cliquet import resource
import colander


class MushroomSchema(resource.ResourceSchema):
    name = colander.SchemaNode(colander.String())


@resource.register()
class Mushroom(resource.BaseResource):
    mapping = MushroomSchema()


@resource.register()
class Toadstool(resource.ProtectedResource):
    mapping = MushroomSchema()
