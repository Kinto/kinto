from cornice import Service
from cliquet import errors
from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet.views.oauth import fxa_conf

params = Service(name='fxa-oauth-params',
                 path='/fxa-oauth/params',
                 error_handler=errors.json_error_handler)


@params.get(permission=NO_PERMISSION_REQUIRED)
def fxa_oauth_params(request):
    """Helper to give Firefox Account configuration information."""
    return {
        'client_id': fxa_conf(request, 'client_id'),
        'oauth_uri': fxa_conf(request, 'oauth_uri'),
        'scope': fxa_conf(request, 'scope'),
    }
