import logging
from concurrent.futures import ThreadPoolExecutor, wait

import colander
import transaction
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import Service


logger = logging.getLogger(__name__)


heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


class HeartbeatResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping(unknown='preserve'))


heartbeat_responses = {
    '200': HeartbeatResponseSchema(
        description="Server is working properly."),
    '503': HeartbeatResponseSchema(
        description="One or more subsystems failing.")
}


@heartbeat.get(permission=NO_PERMISSION_REQUIRED, tags=['Utilities'],
               operation_id='__heartbeat__', response_schemas=heartbeat_responses)
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
            logger.error("'{}' heartbeat failed.".format(future.__heartbeat_name))
            logger.error(exc)

    # Log timed-out heartbeats.
    for future in not_done:
        name = future.__heartbeat_name
        error_msg = "'{}' heartbeat has exceeded timeout of {} seconds."
        logger.error(error_msg.format(name, seconds))

    # If any has failed, return a 503 error response.
    has_error = not all([v or v is None for v in status.values()])
    if has_error:
        request.response.status = 503

    return status


class LbHeartbeatResponseSchema(colander.MappingSchema):
    body = colander.SchemaNode(colander.Mapping())


lbheartbeat_responses = {
    '200': LbHeartbeatResponseSchema(
        description="Returned if server is reachable.")
}


lbheartbeat = Service(name="lbheartbeat", path='/__lbheartbeat__',
                      description="Web head health")


@lbheartbeat.get(permission=NO_PERMISSION_REQUIRED, tags=['Utilities'],
                 operation_id='__lbheartbeat__', response_schemas=lbheartbeat_responses)
def get_lbheartbeat(request):
    """Return successful healthy response.

    If the load-balancer tries to access this URL and fails, this means the
    Web head is not operational and should be dropped.
    """
    status = {}
    return status
