from cliquet import resource
import colander


class MushroomSchema(resource.ResourceSchema):
    name = colander.SchemaNode(colander.String())


@resource.register()
class Mushroom(resource.UserResource):
    mapping = MushroomSchema()


@resource.register()
class Toadstool(resource.ShareableResource):
    mapping = MushroomSchema()


@resource.register()
class Moisture(resource.ShareableResource):
    # Empty schema.
    pass


class PsilocybinSchema(resource.ResourceSchema):
    # Optional fields.
    name = colander.SchemaNode(colander.String(), missing="Unknown")
    edible = colander.SchemaNode(colander.Boolean(), missing=True)
    size = colander.SchemaNode(colander.Integer(), missing=-1)


@resource.register()
class Psilo(resource.ShareableResource):
    mapping = PsilocybinSchema()
