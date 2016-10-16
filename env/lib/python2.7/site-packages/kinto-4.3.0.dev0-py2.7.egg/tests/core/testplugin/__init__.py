from kinto.core import Service
from kinto.core.authorization import RouteFactory


attachment = Service(name='attachment',
                     description='Attach file to record',
                     path='/attachment',
                     factory=RouteFactory)


@attachment.post(permission='attach')
def attachment_post(request):
    return {"ok": True}


def includeme(config):
    config.add_cornice_service(attachment)
