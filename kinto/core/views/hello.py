from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from cliquet import Service, PROTOCOL_VERSION

hello = Service(name="hello", path='/', description="Welcome")


@hello.get(permission=NO_PERMISSION_REQUIRED)
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
        cliquet_protocol_version=PROTOCOL_VERSION,
        url=request.route_url(hello.name)
    )

    eos = get_eos(request)
    if eos:
        data['eos'] = eos

    data['settings'] = {}
    public_settings = request.registry.public_settings
    # Public settings will be prefixed with project name, unless explicitly
    # specified with cliquet. (for retrocompability of clients for example).
    for setting in list(public_settings):
        if setting.startswith('cliquet.'):
            unprefixed = setting.replace('cliquet.', '', 1)
            value = settings[unprefixed]
        elif setting.startswith(project_name + '.'):
            unprefixed = setting.replace(project_name + '.', '')
            value = settings[unprefixed]
        else:
            value = settings[setting]
        data['settings'][setting] = value

    # If current user is authenticated, add user info:
    # (Note: this will call authenticated_userid() with multiauth+groupfinder)
    if Authenticated in request.effective_principals:
        data['user'] = request.get_user_info()

    # Application can register and expose arbitrary capabilities.
    data['capabilities'] = request.registry.api_capabilities

    return data


def get_eos(request):
    return request.registry.settings['eos']
