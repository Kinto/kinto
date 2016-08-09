from kinto.core import Service
from kinto.core.authorization import DYNAMIC as DYNAMIC_PERMISSION
from kinto.core.utils import instance_uri

from kinto.authorization import RouteFactory


def bucket_uri(request):
    matchdict = dict(request.matchdict)
    return instance_uri(request, 'bucket', id=matchdict['bucket_id'])


class StatsRouteFactory(RouteFactory):
    def __init__(self, request):
        """Stats is not a Kinto resource.

        The required permission is:
        * ``read``
        """
        super(StatsRouteFactory, self).__init__(request)
        self.resource_name = 'bucket'
        self.permission_object_id = bucket_uri(request)
        self.required_permission = 'read'


stats = Service(name="stats", path='/buckets/{bucket_id}/stats',
                description="Stats about the bucket.",
                factory=StatsRouteFactory)


@stats.get(permission=DYNAMIC_PERMISSION)
def get_bucket_stats(request):
    bucket_url = bucket_uri(request)

    storage = request.registry.storage

    bucket_info = storage.get('quota', bucket_url, 'bucket_info')
    del bucket_info['id']
    del bucket_info['last_modified']

    return {"data": bucket_info}
