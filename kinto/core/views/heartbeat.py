from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto import logger
from kinto.core import Service


heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""

    # Start executing heartbeats concurrently.
    heartbeats = request.registry.heartbeats
    pool = ThreadPoolExecutor(max_workers=len(heartbeats.keys()))
    futures = []
    for name, callable in heartbeats.items():
        futures.append((name, pool.submit(callable, request)))

    # Wait the results, with timeout.
    seconds = float(request.registry.settings['heartbeat_timeout_seconds'])
    status = {}
    for name, future in futures:
        try:
            status[name] = future.result(timeout=seconds)
        except TimeoutError:
            status[name] = False
            error_msg = "'%s' heartbeat has exceeded timeout of %s seconds."
            logger.exception(error_msg % (name, seconds))

    # If any has failed, return a 503 error response.
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
