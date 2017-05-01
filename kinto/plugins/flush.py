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


def includeme(config):
    config.add_api_capability(
        "flush_endpoint",
        description="The __flush__ endpoint can be used to remove "
                    "all data from all backends.",
        url="https://kinto.readthedocs.io/en/latest/api/1.x/flush.html"
    )
    config.add_cornice_service(flush)
