from cornice.resource import resource
from pyramid.security import Authenticated

from readinglist.resource import BaseResource


@resource(name='device',
          collection_path='/devices',
          path='/devices/{id}',
          description='Collection of devices',
          permission=Authenticated)
class Device(BaseResource):
    pass
