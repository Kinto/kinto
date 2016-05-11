from pyramid import httpexceptions
from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED
from requests.exceptions import HTTPError

from kinto.core import resource
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


class SchemaLess(resource.ResourceSchema):
    class Options:
        preserve_unknown = True


@resource.register()
class Spore(resource.ShareableResource):
    mapping = SchemaLess()


@view_config(context=HTTPError, permission=NO_PERMISSION_REQUIRED)
def response_error(context, request):
    if context.response.status_code == 404:
        error_msg = "Handled in tests/testapp/views.py"
        return httpexceptions.HTTPNotFound(body=error_msg)
    raise context
