import colander
from pyramid.security import NO_PERMISSION_REQUIRED
from cornice.service import get_services

from kinto.core import Service
from kinto.core.api import OpenAPI

swagger = Service(name="swagger", path='/__api__', description="OpenAPI description")


class SwaggerResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown='preserve'))


swagger_response_schemas = {
    '200': SwaggerResponseSchema(
        description='Return an OpenAPI description og the running instance.')
}


@swagger.get(permission=NO_PERMISSION_REQUIRED,
             response_schemas=swagger_response_schemas,
             tags=['Utilities'], operation_id='get_openapi_spec')
def swagger_view(request):

    # Only build json once
    try:
        return swagger_view.__json__
    except AttributeError:
        swagger_view.__json__ = OpenAPI(get_services(), request).generate()
        return swagger_view.__json__
