from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import Service
from kinto.core.storage import KintoObject
from kinto.events import ServerFlushed


flush = Service(name="flush", description="Clear database content", path="/__flush__")


@flush.post(permission=NO_PERMISSION_REQUIRED)
def flush_post(request: Request) -> KintoObject:
    request.registry.storage.flush()  # ty: ignore[unresolved-attribute]
    request.registry.permission.flush()  # ty: ignore[unresolved-attribute]
    request.registry.cache.flush()  # ty: ignore[unresolved-attribute]
    event = ServerFlushed(request)
    request.registry.notify(event)  # ty: ignore[unresolved-attribute]

    request.response.status = 202
    return {}


def includeme(config: Configurator) -> None:
    config.add_api_capability(
        "flush_endpoint",
        description="The __flush__ endpoint can be used to remove all data from all backends.",
        url="https://kinto.readthedocs.io/en/latest/api/1.x/flush.html",
    )
    config.add_cornice_service(flush)
