from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet import Service

heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""
    status = {}

    heartbeats = request.registry.heartbeats
    for name, callable in heartbeats.items():
        status[name] = callable(request)

    has_error = not all([v or v is None for v in status.values()])
    if has_error:
        request.response.status = 503

    return status
