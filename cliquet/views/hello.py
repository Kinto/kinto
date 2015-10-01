import os.path

from dealer.git import Backend
from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet import Service

git = Backend(os.path.dirname(os.path.dirname(__file__)))
hello = Service(name="hello", path='/', description="Welcome")


@hello.get(permission=NO_PERMISSION_REQUIRED)
def get_hello(request):
    """Return information regarding the current instance."""
    settings = request.registry.settings
    project = settings['cliquet.project_name']
    data = dict(
        hello=project,
        version=settings['cliquet.project_version'],
        url=request.route_url(hello.name),
        documentation=settings['cliquet.project_docs']
    )

    eos = get_eos(request)
    if eos:
        data['eos'] = eos

    try:
        data['commit'] = git.revision
    except:
        # In case we are not running from a git repository.
        pass

    public_settings = request.registry.public_settings
    # Public settings should be prefixed with project name, unless explicitly
    # specified with cliquet. (for retrocompability of clients for example).
    for setting in list(public_settings):
        if not (setting.startswith(project) or setting.startswith('cliquet.')):
            public_settings.remove(setting)
            public_settings.add(project + '.' + setting)
    data['settings'] = {k: settings[k] for k in public_settings}

    prefixed_userid = getattr(request, 'prefixed_userid', None)
    if prefixed_userid:
        data['userid'] = prefixed_userid

    return data


def get_eos(request):
    return request.registry.settings['cliquet.eos']
