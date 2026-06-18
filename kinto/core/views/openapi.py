import colander
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import Service
from kinto.core.cornice.service import get_services
from kinto.core.openapi import OpenAPI


openapi = Service(name="openapi", path="/__api__", description="OpenAPI description")


class OpenAPIResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown="preserve"))


openapi_response_schemas = {
    "200": OpenAPIResponseSchema(
        description="Return an OpenAPI description of the running instance."
    )
}


@openapi.get(
    permission=NO_PERMISSION_REQUIRED,
    response_schemas=openapi_response_schemas,
    tags=["Utilities"],
    operation_id="get_openapi_spec",
)
def openapi_view(request) -> dict:
    # Only build json once
    try:
        return openapi_view.__json__
    except AttributeError:
        # ``get_services()`` returns the process-global list of registered
        # services. Restrict it to the ones actually routed by this app, so
        # that services registered elsewhere (e.g. by tests) are not exposed.
        introspector = request.registry.introspector
        services = [
            service
            for service in get_services()
            if introspector.get("routes", getattr(service, "pyramid_route", None) or service.name)
        ]
        openapi_view.__json__ = OpenAPI(services, request).generate()
        return openapi_view.__json__
