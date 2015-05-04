from cornice import Service
from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.settings import asbool


flush = Service(name='flush',
                description='Clear database content',
                path='/__flush__')


@flush.post(permission=NO_PERMISSION_REQUIRED)
def flush_post(request):
    settings = request.registry.settings
    flush_enabled = settings.get('kinto.flush_endpoint_enabled', False)

    if not asbool(flush_enabled):
        raise httpexceptions.HTTPMethodNotAllowed()

    request.registry.storage.flush()
    return httpexceptions.HTTPAccepted()
