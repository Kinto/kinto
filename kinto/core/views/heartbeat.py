from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import Service

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


lbheartbeat = Service(name="lbheartbeat", path='/__lbheartbeat__',
                      description="Web head health")


@lbheartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_lbheartbeat(request):
    """Return successful healthy response.

    If the load-balancer tries to access this URL and fails, this means the
    Web head is not operational and should be dropped.
    """
    status = {}
    return status
