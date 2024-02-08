from kinto.core import Service
from kinto.core.authorization import RouteFactory


attachment = Service(
    name="attachment",
    description="Attach file to object",
    path="/attachment",
    factory=RouteFactory,
)


@attachment.post(permission="attach")
def attachment_post(request):
    return {"ok": True}


log = Service(
    name="log",
    description="Test endpoint without permissions",
    path="/log",
)


@log.get()
def log_get(request):
    return {}


@log.post()
def log_post(request):
    return {}


@log.delete()
def log_delete(request):
    return {}


@log.put()
def log_put(request):
    return {}


@log.patch()
def log_patch(request):
    return {}


def includeme(config):
    config.add_cornice_service(attachment)
    config.add_cornice_service(log)
