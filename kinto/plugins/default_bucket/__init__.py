import uuid

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED, Authenticated
from pyramid.settings import asbool

from kinto.authorization import RouteFactory
from kinto.core import get_user_info as core_get_user_info
from kinto.core.errors import raise_invalid
from kinto.core.events import ACTIONS
from kinto.core.storage.exceptions import UnicityError
from kinto.core.utils import build_request, hmac_digest, instance_uri, reapply_cors, view_lookup
from kinto.views.buckets import Bucket
from kinto.views.collections import Collection


def create_bucket(request, bucket_id):
    """Create a bucket if it doesn't exists."""
    bucket_put = request.method.lower() == "put" and request.path.endswith("buckets/default")
    # Do nothing if current request will already create the bucket.
    if bucket_put:
        return

    # Do not intent to create multiple times per request (e.g. in batch).
    already_created = request.bound_data.setdefault("buckets", {})
    if bucket_id in already_created:
        return

    bucket_uri = instance_uri(request, "bucket", id=bucket_id)
    bucket = resource_create_object(request=request, resource_cls=Bucket, uri=bucket_uri)
    already_created[bucket_id] = bucket


def create_collection(request, bucket_id):
    # Do nothing if current request does not involve a collection.
    subpath = request.matchdict.get("subpath")
    if not (subpath and subpath.rstrip("/").startswith("collections/")):
        return

    collection_id = subpath.split("/")[1]
    collection_uri = instance_uri(request, "collection", bucket_id=bucket_id, id=collection_id)

    # Do not intent to create multiple times per request (e.g. in batch).
    already_created = request.bound_data.setdefault("collections", {})
    if collection_uri in already_created:
        return

    # Do nothing if current request will already create the collection.
    collection_put = request.method.lower() == "put" and request.path.endswith(collection_id)
    if collection_put:
        return

    collection = resource_create_object(
        request=request, resource_cls=Collection, uri=collection_uri
    )
    already_created[collection_uri] = collection


def resource_create_object(request, resource_cls, uri):
    """Implicitly create a resource (or fail silently).

    In the default bucket, the bucket and collection are implicitly
    created. This helper creates one of those resources using a
    simulated request and context that is appropriate for the
    resource. Also runs create events as though the resource were
    created in a subrequest.

    If the resource already exists, do nothing.

    """
    resource_name, matchdict = view_lookup(request, uri)

    # Build a fake request, mainly used to populate the create events that
    # will be triggered by the resource.
    fakerequest = build_request(request, {"method": "PUT", "path": uri})
    fakerequest.matchdict = matchdict
    fakerequest.bound_data = request.bound_data
    fakerequest.authn_type = request.authn_type
    fakerequest.selected_userid = request.selected_userid
    fakerequest.errors = request.errors
    fakerequest.current_resource_name = resource_name

    obj_id = matchdict["id"]

    # Fake context, required to instantiate a resource.
    context = RouteFactory(fakerequest)
    context.resource_name = resource_name
    resource = resource_cls(fakerequest, context)

    # Check that provided id is valid for this resource.
    if not resource.model.id_generator.match(obj_id):
        error_details = {"location": "path", "description": f"Invalid {resource_name} id"}
        raise_invalid(resource.request, **error_details)

    data = {"id": obj_id}
    try:
        obj = resource.model.create_object(data)
    except UnicityError:
        # The record already exists; skip running events
        return {}

    # Since the current request is not a resource (but a straight Service),
    # we simulate a request on a resource.
    # This will be used in the resource event payload.
    resource.postprocess(obj, action=ACTIONS.CREATE)
    return obj


def default_bucket(request):
    if request.method.lower() == "options":
        path = request.path.replace("default", "unknown")
        subrequest = build_request(request, {"method": "OPTIONS", "path": path})
        return request.invoke_subrequest(subrequest)

    if Authenticated not in request.effective_principals:
        # Pass through the forbidden_view_config
        raise httpexceptions.HTTPForbidden()

    settings = request.registry.settings

    if asbool(settings["readonly"]):
        raise httpexceptions.HTTPMethodNotAllowed()

    bucket_id = request.default_bucket_id

    # Implicit object creations.
    # Make sure bucket exists
    create_bucket(request, bucket_id)
    # Make sure the collection exists
    create_collection(request, bucket_id)

    path = request.path.replace("/buckets/default", f"/buckets/{bucket_id}")
    querystring = request.url[(request.url.index(request.path) + len(request.path)) :]
    try:
        # If 'id' is provided as 'default', replace with actual bucket id.
        body = request.json
        body["data"]["id"] = body["data"]["id"].replace("default", bucket_id)
    except Exception:
        body = request.body or {"data": {}}
    subrequest = build_request(
        request, {"method": request.method, "path": path + querystring, "body": body}
    )
    subrequest.bound_data = request.bound_data

    try:
        response = request.invoke_subrequest(subrequest)
    except httpexceptions.HTTPException as error:
        is_redirect = error.status_code < 400
        if error.content_type == "application/json" or is_redirect:
            response = reapply_cors(subrequest, error)
        else:
            # Ask the upper level to format the error.
            raise error
    return response


def default_bucket_id(request):
    settings = request.registry.settings
    secret = settings.get("default_bucket_hmac_secret", settings["userid_hmac_secret"])
    # Build the user unguessable bucket_id UUID from its user_id
    digest = hmac_digest(secret, request.prefixed_userid)
    return str(uuid.UUID(digest[:32]))


def get_user_info(request):
    user_info = {**core_get_user_info(request), "bucket": request.default_bucket_id}
    return user_info


def includeme(config):
    # Redirect default to the right endpoint
    config.add_view(default_bucket, route_name="default_bucket", permission=NO_PERMISSION_REQUIRED)
    config.add_view(
        default_bucket, route_name="default_bucket_collection", permission=NO_PERMISSION_REQUIRED
    )

    config.add_route("default_bucket_collection", "/buckets/default/{subpath:.*}")
    config.add_route("default_bucket", "/buckets/default")

    # Provide helpers
    config.add_request_method(default_bucket_id, reify=True)
    # Override kinto.core default user info
    config.add_request_method(get_user_info)

    config.add_api_capability(
        "default_bucket",
        description="The default bucket is an alias for a personal"
        " bucket where collections are created implicitly.",
        url="https://kinto.readthedocs.io/en/latest/api/1.x/"
        "buckets.html#personal-bucket-default",
    )
