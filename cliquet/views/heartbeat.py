import requests
from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED
from six.moves.urllib.parse import urljoin
from fxa.oauth import Client as OAuthClient

heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""
    database = request.db.ping()
    cache = request.cache.ping()

    settings = request.registry.settings
    server_url = settings['fxa-oauth.oauth_uri']

    oauth = None
    if server_url is not None:
        auth_client = OAuthClient(server_url=server_url)
        server_url = auth_client.server_url
        oauth = False

        try:
            r = requests.get(urljoin(server_url, '/__heartbeat__'), timeout=10)
            r.raise_for_status()
            oauth = True
        except requests.exceptions.HTTPError:
            pass

    status = dict(database=database, cache=cache, oauth=oauth)
    has_error = not all([v for v in status.values()])

    if has_error:
        request.response.status = 503

    return status
