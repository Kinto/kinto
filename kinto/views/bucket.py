from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED


buckets = Service(name="buckets", path='/buckets',
                  description="Buckets list you have read or write access to.")

bucket = Service(name="bucket", path='/buckets/{bucket_id}',
                 description="Bucket resource")


@buckets.get(permission=NO_PERMISSION_REQUIRED)
def get_buckets(request):
    """Return a list of buckets the connected user have got access to."""
    user_buckets = [request.authenticated_userid]
    # XXX: Todo query the list of buckets the user is admin to.

    request.response.headers['Content-Type'] = 'application/vnd.api+json'
    result = {}
    result['links'] = {
        "self": request.route_url(buckets.name)
    }
    result['data'] = [
        {
            "type": "bucket",
            "id": '/buckets/%s' % bucket_id
        } for bucket_id in user_buckets
    ]
    return result


@bucket.get(permission=NO_PERMISSION_REQUIRED)
def get_bucket(request):
    bucket_id = '/buckets/%s' % request.matchdict['bucket_id']
    # XXX: Read principal from the permission backend
    # get_principals = request.permissions.get_object_permission_principals

    request.response.headers['Content-Type'] = 'application/vnd.api+json'

    return {
        'links': {
            'self': request.route_url(bucket.name, **request.matchdict),
            'related': '%s/collections' % request.route_url(
                bucket.name, **request.matchdict)
        },
        'data': {
            'type': 'bucket',
            'id': bucket_id,
            'permissions': {
                'write': [],  # get_principals(bucket_id, 'write'),
                'read': [],  # get_principals(bucket_id, 'read'),
                'collections:create': [],  # get_principals(bucket_id,
                                           #           'collections:create'),
                'groups:create': [],
                # get_principals(bucket_id, 'groups:create')
            }
        }
    }
