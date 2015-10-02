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
    project_name = settings['project_name']
    data = dict(
        hello=project_name,
        version=settings['project_version'],
        url=request.route_url(hello.name),
        documentation=settings['project_docs']
    )

    eos = get_eos(request)
    if eos:
        data['eos'] = eos

    try:
        data['commit'] = git.revision
    except:
        # In case we are not running from a git repository.
        pass

    data['settings'] = {}
    public_settings = request.registry.public_settings
    # Public settings will be prefixed with project name, unless explicitly
    # specified with cliquet. (for retrocompability of clients for example).
    for setting in list(public_settings):
        if setting.startswith('cliquet.'):
            value = settings[setting.replace('cliquet.', '', 1)]
        else:
            setting = setting.replace(project_name + '.', '')
            value = settings[setting]
            setting = project_name + '.' + setting
        data['settings'][setting] = value

    prefixed_userid = getattr(request, 'prefixed_userid', None)
    if prefixed_userid:
        data['userid'] = prefixed_userid

    return data


def get_eos(request):
    return request.registry.settings['eos']
