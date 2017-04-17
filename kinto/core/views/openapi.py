import colander
from pyramid.security import NO_PERMISSION_REQUIRED
from cornice.service import get_services

from kinto.core import Service
from kinto.core.openapi import OpenAPI


openapi = Service(name="openapi", path='/__api__', description="OpenAPI description")


class OpenAPIResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown='preserve'))


openapi_response_schemas = {
    '200': OpenAPIResponseSchema(
        description='Return an OpenAPI description of the running instance.')
}


@openapi.get(permission=NO_PERMISSION_REQUIRED,
             response_schemas=openapi_response_schemas,
             tags=['Utilities'], operation_id='get_openapi_spec')
def openapi_view(request):

    # Only build json once
    try:
        return openapi_view.__json__
    except AttributeError:
        openapi_view.__json__ = OpenAPI(get_services(), request).generate()
        return openapi_view.__json__
