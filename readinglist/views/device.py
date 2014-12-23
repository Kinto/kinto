from cornice.resource import resource
from pyramid.security import Authenticated
from colander import SchemaNode, String

from readinglist.resource import BaseResource, RessourceSchema


class DeviceSchema(RessourceSchema):
    name = SchemaNode(String())


@resource(collection_path='/devices',
          path='/devices/{id}',
          description='Collection of devices',
          permission=Authenticated)
class Device(BaseResource):
    mapping = DeviceSchema()
