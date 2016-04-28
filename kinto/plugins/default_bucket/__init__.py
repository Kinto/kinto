import uuid

import six
from pyramid import httpexceptions
from pyramid.settings import asbool
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated

from cliquet.errors import raise_invalid
from cliquet.events import ACTIONS
from cliquet.utils import build_request, reapply_cors, hmac_digest
from cliquet.storage import exceptions as storage_exceptions

from kinto.authorization import RouteFactory
from kinto.views.buckets import Bucket
from kinto.views.collections import Collection


def create_bucket(request, bucket_id):
    """Create a bucket if it doesn't exists."""
    bucket_put = (request.method.lower() == 'put' and
                  request.path.endswith('buckets/default'))
    # Do nothing if current request will already create the bucket.
    if bucket_put:
        return

    # Do not intent to create multiple times per request (e.g. in batch).
    already_created = request.bound_data.setdefault('buckets', {})
    if bucket_id in already_created:
        return

    bucket = resource_create_object(request=request,
                                    resource_cls=Bucket,
                                    uri='/buckets/%s' % bucket_id,
                                    resource_name='bucket',
                                    obj_id=bucket_id)
    already_created[bucket_id] = bucket


def create_collection(request, bucket_id):
    # Do nothing if current request does not involve a collection.
    subpath = request.matchdict.get('subpath')
    if not (subpath and subpath.startswith('collections/')):
        return

    collection_id = subpath.split('/')[1]
    collection_uri = '/buckets/%s/collections/%s' % (bucket_id, collection_id)

    # Do not intent to create multiple times per request (e.g. in batch).
    already_created = request.bound_data.setdefault('collections', {})
    if collection_uri in already_created:
        return

    # Do nothing if current request will already create the collection.
    collection_put = (request.method.lower() == 'put' and
                      request.path.endswith(collection_id))
    if collection_put:
        return

    backup_matchdict = request.matchdict
    request.matchdict = dict(bucket_id=bucket_id,
                             id=collection_id,
                             **request.matchdict)
    collection = resource_create_object(request=request,
                                        resource_cls=Collection,
                                        uri=collection_uri,
                                        resource_name='collection',
                                        obj_id=collection_id)
    already_created[collection_uri] = collection
    request.matchdict = backup_matchdict


def resource_create_object(request, resource_cls, uri, resource_name, obj_id):
    """In the default bucket, the bucket and collection are implicitly
    created. This helper instantiate the resource and simulate a request
    with its RootFactory on the instantiated resource.
    :returns: the created object
    :rtype: dict
    """
    # Fake context to instantiate a resource.
    context = RouteFactory(request)
    context.get_permission_object_id = lambda r, i: uri

    resource = resource_cls(request, context)

    # Check that provided id is valid for this resource.
    if not resource.model.id_generator.match(obj_id):
        error_details = {
            'location': 'path',
            'description': "Invalid %s id" % resource_name
        }
        raise_invalid(resource.request, **error_details)

    data = {'id': obj_id}
    try:
        obj = resource.model.create_record(data)
        # Since the current request is not a resource (but a straight Service),
        # we simulate a request on a resource.
        # This will be used in the resource event payload.
        resource.request.current_resource_name = resource_name
        resource.postprocess(data, action=ACTIONS.CREATE)
    except storage_exceptions.UnicityError as e:
        obj = e.record
    return obj


def default_bucket(request):
    if request.method.lower() == 'options':
        path = request.path.replace('default', 'unknown')
        subrequest = build_request(request, {
            'method': 'OPTIONS',
            'path': path
        })
        return request.invoke_subrequest(subrequest)

    if Authenticated not in request.effective_principals:
        # Pass through the forbidden_view_config
        raise httpexceptions.HTTPForbidden()

    settings = request.registry.settings

    if asbool(settings['readonly']):
        raise httpexceptions.HTTPMethodNotAllowed()

    bucket_id = request.default_bucket_id
    path = request.path.replace('/buckets/default', '/buckets/%s' % bucket_id)
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
    subrequest.bound_data = request.bound_data

    try:
        response = request.invoke_subrequest(subrequest)
    except httpexceptions.HTTPException as error:
        is_redirect = error.status_code < 400
        if error.content_type == 'application/json' or is_redirect:
            response = reapply_cors(subrequest, error)
        else:
            # Ask the upper level to format the error.
            raise error
    return response


def default_bucket_id(request):
    settings = request.registry.settings
    secret = settings['userid_hmac_secret']
    # Build the user unguessable bucket_id UUID from its user_id
    digest = hmac_digest(secret, request.prefixed_userid)
    return six.text_type(uuid.UUID(digest[:32]))


def get_user_info(request):
    user_info = {
        'id': request.prefixed_userid,
        'bucket': request.default_bucket_id
    }
    return user_info


def includeme(config):
    # Redirect default to the right endpoint
    config.add_view(default_bucket,
                    route_name='default_bucket',
                    permission=NO_PERMISSION_REQUIRED)
    config.add_view(default_bucket,
                    route_name='default_bucket_collection',
                    permission=NO_PERMISSION_REQUIRED)

    config.add_route('default_bucket_collection',
                     '/buckets/default/{subpath:.*}')
    config.add_route('default_bucket', '/buckets/default')

    # Provide helpers
    config.add_request_method(default_bucket_id, reify=True)
    # Override Cliquet default user info
    config.add_request_method(get_user_info)

    config.add_api_capability(
        "default_bucket",
        description="The default bucket is an alias for a personal"
                    " bucket where collections are created implicitly.",
        url="http://kinto.readthedocs.io/en/latest/api/1.x/"
            "buckets.html#personal-bucket-default")
