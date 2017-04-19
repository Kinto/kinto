import json

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


def record_size(record):
    return len(json.dumps(record, sort_keys=True, separators=(',', ':')))


@stats.get(permission=DYNAMIC_PERMISSION)
def get_bucket_stats(request):
    bucket_url = bucket_uri(request)
    collections, collection_count = request.registry.storage.get_all(
        'collection', bucket_url)

    record_count = 0
    storage_size = 0
    for collection in collections:
        collection_url = instance_uri(request, 'collection',
                                      bucket_id=request.matchdict['bucket_id'],
                                      id=collection['id'])
        records, count = request.registry.storage.get_all(
            'record', collection_url)

        if count > 0:
            storage_size += sum([record_size(r) for r in records])
            record_count += count

    return {
        "collection_count": collection_count,
        "record_count": record_count,
        "storage_size": storage_size,
    }
