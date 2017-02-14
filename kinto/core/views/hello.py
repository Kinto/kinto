import colander
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from kinto.core import Service

hello = Service(name="hello", path='/', description="Welcome")


class HelloResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown='preserve'))


hello_response_schemas = {
    '200': HelloResponseSchema(
        description='Return information about the running Instance.')
}


@hello.get(permission=NO_PERMISSION_REQUIRED, tags=['Utilities'],
           operation_id='server_info', response_schemas=hello_response_schemas)
def get_hello(request):
    """Return information regarding the current instance."""
    settings = request.registry.settings
    project_name = settings['project_name']
    project_version = settings['project_version']
    data = dict(
        project_name=project_name,
        project_version=project_version,
        http_api_version=settings['http_api_version'],
        project_docs=settings['project_docs'],
        url=request.route_url(hello.name)
    )

    eos = get_eos(request)
    if eos:
        data['eos'] = eos

    data['settings'] = {}
    public_settings = request.registry.public_settings
    for setting in list(public_settings):
        data['settings'][setting] = settings[setting]

    # If current user is authenticated, add user info:
    # (Note: this will call authenticated_userid() with multiauth+groupfinder)
    if Authenticated in request.effective_principals:
        data['user'] = request.get_user_info()

    # Application can register and expose arbitrary capabilities.
    data['capabilities'] = request.registry.api_capabilities

    return data


def get_eos(request):
    return request.registry.settings['eos']
