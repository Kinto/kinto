from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED


hello = Service(name="hello", path='/', description="Welcome")


@hello.get(permission=NO_PERMISSION_REQUIRED)
def get_hello(request):
    """Return information regarding the current instance."""
    settings = request.registry.settings
    data = dict(
        hello=settings['cliquet.project_name'],
        version=settings['cliquet.project_version'],
        url=request.host_url,
        documentation=settings['cliquet.project_docs']
    )

    eos = get_eos(request)
    if eos:
        data['eos'] = eos

    return data


def get_eos(request):
    return request.registry.settings['cliquet.eos']
