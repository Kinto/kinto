from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED

heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""
    database = request.db.ping()

    status = dict(database=database)
    has_error = not all([v for v in status.values()])
    if has_error:
        request.response.status = 503

    return status
