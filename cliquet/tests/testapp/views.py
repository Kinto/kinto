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


@resource.register()
class Moisture(resource.ProtectedResource):
    # Empty schema.
    pass


class PsilocybinSchema(resource.ResourceSchema):
    # Optional fields.
    name = colander.SchemaNode(colander.String(), missing="Unknown")
    edible = colander.SchemaNode(colander.Boolean(), missing=True)
    size = colander.SchemaNode(colander.Integer(), missing=-1)


@resource.register()
class Psilo(resource.ProtectedResource):
    mapping = PsilocybinSchema()
