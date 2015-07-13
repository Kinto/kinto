from six import text_type
from uuid import UUID

from pyramid.httpexceptions import (HTTPForbidden, HTTPPreconditionFailed,
                                    HTTPException)
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.view import view_config

from cliquet import resource
from cliquet.utils import hmac_digest, build_request, reapply_cors

from kinto.views import NameGenerator


def create_bucket(request, bucket_id):
    """Create a bucket if it doesn't exists."""
    bucket_put = (request.method.lower() == 'put' and
                  request.path.endswith('buckets/default'))

    if not bucket_put:
        subrequest = build_request(request, {
            'method': 'PUT',
            'path': '/buckets/%s' % bucket_id,
            'body': {"data": {}},
            'headers': {'If-None-Match': '*'.encode('utf-8')}
        })

        try:
            request.invoke_subrequest(subrequest)
        except HTTPPreconditionFailed:
            # The bucket already exists
            pass


def create_collection(request, bucket_id):
    subpath = request.matchdict['subpath']
    if subpath.startswith('/collections/'):
        collection_id = subpath.split('/')[2]
        collection_put = (request.method.lower() == 'put' and
                          request.path.endswith(collection_id))
        if not collection_put:
            subrequest = build_request(request, {
                'method': 'PUT',
                'path': '/buckets/%s/collections/%s' % (
                    bucket_id, collection_id),
                'body': {"data": {}},
                'headers': {'If-None-Match': '*'.encode('utf-8')}
            })
            try:
                request.invoke_subrequest(subrequest)
            except HTTPPreconditionFailed:
                # The collection already exists
                pass


@view_config(route_name='default_bucket', permission=NO_PERMISSION_REQUIRED)
def default_bucket(request):
    if request.method.lower() == 'options':
        path = request.path.replace('default', 'unknown')
        subrequest = build_request(request, {
            'method': 'OPTIONS',
            'path': path
        })
        return request.invoke_subrequest(subrequest)

    if getattr(request, 'prefixed_userid', None) is None:
        raise HTTPForbidden  # Pass through the forbidden_view_config

    settings = request.registry.settings
    hmac_secret = settings['cliquet.userid_hmac_secret']
    # Build the user unguessable bucket_id UUID from its user_id
    digest = hmac_digest(hmac_secret, request.prefixed_userid)
    bucket_id = text_type(UUID(digest[:32]))
    path = request.path.replace('default', bucket_id)
    querystring = request.url[(request.url.index(request.path) +
                               len(request.path)):]

    # Make sure bucket exists
    create_bucket(request, bucket_id)

    # Make sure the collection exists
    create_collection(request, bucket_id)

    subrequest = build_request(request, {
        'method': request.method,
        'path': path + querystring,
        'body': request.body
    })

    try:
        response = request.invoke_subrequest(subrequest)
    except HTTPException as error:
        response = reapply_cors(subrequest, error)
    return response


@resource.register(name='bucket',
                   collection_methods=('GET',),
                   collection_path='/buckets',
                   record_path='/buckets/{{id}}')
class Bucket(resource.ProtectedResource):
    permissions = ('read', 'write', 'collection:create', 'group:create')

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        self.collection.id_generator = NameGenerator()

    def get_parent_id(self, request):
        # Buckets are not isolated by user, unlike Cliquet resources.
        return ''

    def delete(self):
        result = super(Bucket, self).delete()

        # Delete groups.
        storage = self.collection.storage
        parent_id = '/buckets/%s' % self.record_id
        storage.delete_all(collection_id='group', parent_id=parent_id)

        # Delete collections.
        deleted = storage.delete_all(collection_id='collection',
                                     parent_id=parent_id)

        # Delete records.
        id_field = self.collection.id_field
        for collection in deleted:
            parent_id = '/buckets/%s/collections/%s' % (self.record_id,
                                                        collection[id_field])
            storage.delete_all(collection_id='record', parent_id=parent_id)

        return result
