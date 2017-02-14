from pyramid.security import NO_PERMISSION_REQUIRED
from cornice.service import get_services

from kinto.core import Service
from kinto.core.api import OpenAPI

swagger = Service(name="swagger", path='/__api__', description="OpenAPI description")


@swagger.get(permission=NO_PERMISSION_REQUIRED)
def swagger_view(request):

    # Only build json once
    try:
        return swagger_view.__json__
    except AttributeError:
        swagger_view.__json__ = OpenAPI(get_services(), request).generate()
        return swagger_view.__json__
