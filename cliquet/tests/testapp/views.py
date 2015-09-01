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

    def get_parent_id(self, request):
        return "foobar"


@resource.register()
class Moisture(resource.ProtectedResource):
    # Empty schema.
    pass


class PsilocybinSchema(resource.ResourceSchema):
    # Optional fields.
    edible = colander.SchemaNode(colander.Boolean(), missing=True)


@resource.register()
class Psilo(resource.ProtectedResource):
    mapping = PsilocybinSchema()
