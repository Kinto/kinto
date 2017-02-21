from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.events import ServerFlushed

flush = Service(name='flush',
                description='Clear database content',
                path='/__flush__')


@flush.post(permission=NO_PERMISSION_REQUIRED)
def flush_post(request):
    request.registry.storage.flush()
    request.registry.permission.flush()
    request.registry.cache.flush()
    event = ServerFlushed(request)
    request.registry.notify(event)

    request.response.status = 202
    return {}
