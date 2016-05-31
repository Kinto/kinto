from multiprocessing import TimeoutError
from multiprocessing.pool import ThreadPool
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto import logger
from kinto.core import Service


heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""
    heartbeats = request.registry.heartbeats
    seconds = float(request.registry.settings['heartbeat_timeout_seconds'])

    pool = ThreadPool(processes=1)

    async_results = []
    for name, callable in heartbeats.items():
        async_results.append((name, pool.apply_async(callable, (request,))))

    status = {}
    for name, async_result in async_results:
        try:
            status[name] = async_result.get(timeout=seconds)
        except TimeoutError:
            error_msg = "'%s' heartbeat has exceeded timeout of %s seconds."
            logger.exception(error_msg % (name, seconds))

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
