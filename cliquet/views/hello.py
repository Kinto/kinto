from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet import Service

hello = Service(name="hello", path='/', description="Welcome")


@hello.get(permission=NO_PERMISSION_REQUIRED)
def get_hello(request):
    """Return information regarding the current instance."""
    settings = request.registry.settings
    data = dict(
        hello=settings['cliquet.project_name'],
        version=settings['cliquet.project_version'],
        url=request.route_url(hello.name),
        documentation=settings['cliquet.project_docs']
    )

    eos = get_eos(request)
    if eos:
        data['eos'] = eos

    return data


def get_eos(request):
    return request.registry.settings['cliquet.eos']
