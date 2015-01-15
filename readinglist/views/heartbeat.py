from cornice import Service

heartbeat = Service(name="heartbeat", path='/__heartbeat__',
                    description="Server health")


@heartbeat.get()
def get_heartbeat(request):
    """Return information about server health."""
    try:
        request.db.ping()
        database = True
    except:
        database = False

    status = dict(database=database)
    has_error = not all([v for v in status.values()])
    if has_error:
        request.response.status = 503

    return status
