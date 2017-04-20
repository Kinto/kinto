from concurrent.futures import ThreadPoolExecutor, wait

import transaction
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto import logger
from kinto.core import Service


heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get(permission=NO_PERMISSION_REQUIRED)
def get_heartbeat(request):
    """Return information about server health."""
    status = {}

    def heartbeat_check(name, func):
        status[name] = False
        status[name] = func(request)
        # Since the heartbeat checks run concurrently, their transactions
        # overlap and might end in shared lock errors. By aborting here
        # we clean-up the state on each heartbeat call instead of once at the
        # end of the request. See bug Kinto/kinto#804
        transaction.abort()

    # Start executing heartbeats concurrently.
    heartbeats = request.registry.heartbeats
    pool = ThreadPoolExecutor(max_workers=max(1, len(heartbeats.keys())))
    futures = []
    for name, func in heartbeats.items():
        future = pool.submit(heartbeat_check, name, func)
        future.__heartbeat_name = name  # For logging purposes.
        futures.append(future)

    # Wait for the results, with timeout.
    seconds = float(request.registry.settings['heartbeat_timeout_seconds'])
    done, not_done = wait(futures, timeout=seconds)

    # A heartbeat is supposed to return True or False, and never raise.
    # Just in case, go though results to spot any potential exception.
    for future in done:
        exc = future.exception()
        if exc is not None:
            logger.error("%r heartbeat failed." % future.__heartbeat_name)
            logger.error(exc)

    # Log timed-out heartbeats.
    for future in not_done:
        name = future.__heartbeat_name
        error_msg = "%r heartbeat has exceeded timeout of %s seconds."
        logger.error(error_msg % (name, seconds))

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
