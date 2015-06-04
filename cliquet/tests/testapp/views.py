from cliquet import resource
from cliquet import authorization
import colander


class MushroomSchema(resource.ResourceSchema):
    name = colander.SchemaNode(colander.String())


service_arguments = {'factory': authorization.RouteFactory}
service_arguments.update(resource.ViewSet.service_arguments)


@resource.register(service_arguments=service_arguments)
class Mushroom(resource.BaseResource):
    mapping = MushroomSchema()
