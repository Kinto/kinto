from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet.authentication import fxa_ping

heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""
    database = request.db.ping()
    cache = request.cache.ping()
    oauth = fxa_ping(request)

    status = dict(database=database, cache=cache, oauth=oauth)

    has_error = not all([v for v in status.values()])
    if has_error:
        request.response.status = 503

    return status
