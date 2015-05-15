from cornice import Service
from pyramid.security import NO_PERMISSION_REQUIRED


buckets = Service(name="buckets", path='/buckets',
                  description="List of bucket's you have access to")


@buckets.get(permission=NO_PERMISSION_REQUIRED)
def get_buckets(request):
    """Return a list of buckets the connected user have got access to."""
    data = {
        "buckets": [request.authenticated_userid]
    }
    return data
