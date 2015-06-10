from cliquet import resource
from cliquet import authorization
import colander


class MushroomSchema(resource.ResourceSchema):
    name = colander.SchemaNode(colander.String())


@resource.register(factory=authorization.RouteFactory)
class Mushroom(resource.BaseResource):
    mapping = MushroomSchema()


@resource.register(factory=authorization.RouteFactory)
class Toadstool(resource.ProtectedResource):
    mapping = MushroomSchema()
