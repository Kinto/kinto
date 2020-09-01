import collections
import hashlib
import hmac
import math
import os
import re
import time
from base64 import b64decode, b64encode
from binascii import hexlify
from enum import Enum
from urllib.parse import unquote

import jsonpatch
import ujson as json
from colander import null
from cornice import cors
from pyramid import httpexceptions
from pyramid.interfaces import IRoutesMapper
from pyramid.request import Request, apply_request_extensions
from pyramid.security import Authenticated
from pyramid.settings import aslist
from pyramid.view import render_view_to_response

try:
    import sqlalchemy
except ImportError:  # pragma: no cover
    sqlalchemy = None

try:
    import memcache
except ImportError:  # pragma: no cover
    memcache = None


def json_serializer(v, **kw):
    return json.dumps(v, escape_forward_slashes=False)


def strip_whitespace(v):
    """Remove whitespace, newlines, and tabs from the beginning/end
    of a string.

    :param str v: the string to strip.
    :rtype: str
    """
    return v.strip(" \t\n\r") if v is not null else v


def msec_time():
    """Return current epoch time in milliseconds.

    :rtype: int
    """
    return int(time.time() * 1000.0)  # floor


def classname(obj):
    """Get a classname from an object.

    :rtype: str
    """
    return obj.__class__.__name__.lower()


def merge_dicts(a, b):
    """Merge b into a recursively, without overwriting values.

    :param dict a: the dict that will be altered with values of `b`.
    """
    for k, v in b.items():
        if isinstance(v, dict):
            merge_dicts(a.setdefault(k, {}), v)
        else:
            a.setdefault(k, v)


def recursive_update_dict(root, changes, ignores=()):
    """Update recursively all the entries from a dict and it's children dicts.

    :param dict root: root dictionary
    :param dict changes: dictonary where changes should be made (default=root)
    :returns dict newd: dictionary with removed entries of val.
    """
    if isinstance(changes, dict):
        for k, v in changes.items():
            if isinstance(v, dict):
                if k not in root:
                    root[k] = {}
                recursive_update_dict(root[k], v, ignores)
            elif v in ignores:
                if k in root:
                    root.pop(k)
            else:
                root[k] = v


def random_bytes_hex(bytes_length):
    """Return a hexstring of bytes_length cryptographic-friendly random bytes.

    :param int bytes_length: number of random bytes.
    :rtype: str
    """
    return hexlify(os.urandom(bytes_length)).decode("utf-8")


def native_value(value):
    """Convert string value to native python values.

    :param str value: value to interprete.
    :returns: the value coerced to python type
    """
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
            if parsed_value != math.inf:
                value = parsed_value
        except ValueError:
            return value
    return value


def read_env(key, value):
    """Read the setting key from environment variables.

    :param key: the setting name
    :param value: default value if undefined in environment
    :returns: the value from environment, coerced to python type, or the (uncoerced) default value
    """
    envkey = key.replace(".", "_").replace("-", "_").upper()
    if envkey in os.environ:
        return native_value(os.environ[envkey])
    return value


def encode64(content, encoding="utf-8"):
    """Encode some content in base64.

    :rtype: str
    """
    return b64encode(content.encode(encoding)).decode(encoding)


def decode64(encoded_content, encoding="utf-8"):
    """Decode some base64 encoded content.

    :rtype: str
    """
    return b64decode(encoded_content.encode(encoding)).decode(encoding)


def hmac_digest(secret, message, encoding="utf-8"):
    """Return hex digest of a message HMAC using secret"""
    if isinstance(secret, str):
        secret = secret.encode(encoding)
    return hmac.new(secret, message.encode(encoding), hashlib.sha256).hexdigest()


def dict_subset(d, keys):
    """Return a dict with the specified keys"""
    result = {}

    for key in keys:
        if "." in key:
            field, subfield = key.split(".", 1)
            if isinstance(d.get(field), collections.Mapping):
                subvalue = dict_subset(d[field], [subfield])
                result[field] = dict_merge(subvalue, result.get(field, {}))
            elif field in d:
                result[field] = d[field]
        else:
            if key in d:
                result[key] = d[key]

    return result


def dict_merge(a, b):
    """Merge the two specified dicts"""
    result = dict(**b)
    for key, value in a.items():
        if isinstance(value, collections.Mapping):
            value = dict_merge(value, result.setdefault(key, {}))
        result[key] = value
    return result


def find_nested_value(d, path, default=None):
    """Finds a nested value in a dict from a dotted path key string.

    :param dict d: the dict to retrieve nested value from
    :param str path: the path to the nested value, in dot notation
    :returns: the nested value if any was found, or None
    """
    if path in d:
        return d.get(path)

    # the challenge is to identify what is the root key, as dict keys may
    # contain dot characters themselves
    parts = path.split(".")

    # build a list of all possible root keys from all the path parts
    candidates = [".".join(parts[: i + 1]) for i in range(len(parts))]

    # we start with the longest candidate paths as they're most likely to be the
    # ones we want if they match
    root = next((key for key in reversed(candidates) if key in d), None)

    # if no valid root candidates were found, the path is invalid; abandon
    if root is None or not isinstance(d.get(root), dict):
        return default

    # we have our root key, extract the new subpath and recur
    subpath = path.replace(root + ".", "", 1)
    return find_nested_value(d.get(root), subpath, default=default)


class COMPARISON(Enum):
    LT = "<"
    MIN = ">="
    MAX = "<="
    NOT = "!="
    EQ = "=="
    GT = ">"
    IN = "in"
    EXCLUDE = "exclude"
    LIKE = "like"
    HAS = "has"
    # The order matters here because we want to match
    # contains_any before contains_
    CONTAINS_ANY = "contains_any"
    CONTAINS = "contains"


def reapply_cors(request, response):
    """Reapply cors headers to the new response with regards to the request.

    We need to re-apply the CORS checks done by Cornice, in case we're
    recreating the response from scratch.

    """
    service = request.current_service
    if service:
        request.info["cors_checked"] = False
        cors.apply_cors_post_request(service, request, response)
        response = cors.ensure_origin(service, request, response)
    else:
        # No existing service is concerned, and Cornice is not implied.
        origin = request.headers.get("Origin")
        if origin:
            settings = request.registry.settings
            allowed_origins = set(aslist(settings["cors_origins"]))
            required_origins = {"*", origin}
            if allowed_origins.intersection(required_origins):
                response.headers["Access-Control-Allow-Origin"] = origin

        # Import service here because kinto.core import utils
        from kinto.core import Service

        if Service.default_cors_headers:  # pragma: no branch
            headers = ",".join(Service.default_cors_headers)
            response.headers["Access-Control-Expose-Headers"] = headers
    return response


def log_context(request, **kwargs):
    """Bind information to the current request summary log."""
    non_empty = {k: v for k, v in kwargs.items() if v is not None}
    try:
        request._log_context.update(**non_empty)
    except AttributeError:
        request._log_context = non_empty
    return request._log_context


def current_service(request):
    """Return the Cornice service matching the specified request.

    :returns: the service or None if unmatched.
    :rtype: cornice.Service
    """
    if request.matched_route:
        services = request.registry.cornice_services
        pattern = request.matched_route.pattern
        try:
            service = services[pattern]
        except KeyError:
            return None
        else:
            return service


def current_resource_name(request):
    """Return the name used when the kinto.core resource was registered along its
    viewset.

    :returns: the resource identifier.
    :rtype: str
    """
    service = current_service(request)
    resource_name = service.viewset.get_name(service.resource)
    return resource_name


def prefixed_userid(request):
    """In Kinto users ids are prefixed with the policy name that is
    contained in Pyramid Multiauth.
    If a custom authn policy is used, without authn_type, this method returns
    the user id without prefix.
    """
    # If pyramid_multiauth is used, a ``authn_type`` is set on request
    # when a policy succesfully authenticates a user.
    # (see :func:`kinto.core.initialization.setup_authentication`)
    authn_type = getattr(request, "authn_type", None)
    if authn_type is not None:
        return f"{authn_type}:{request.selected_userid}"


def prefixed_principals(request):
    """
    :returns: the list principals with prefixed user id.
    """
    principals = request.effective_principals
    if Authenticated not in principals:
        return principals

    # Remove unprefixed user id on effective_principals to avoid conflicts.
    # (it is added via Pyramid Authn policy effective principals)
    prefix, userid = request.prefixed_userid.split(":", 1)
    principals = [p for p in principals if p != userid]

    if request.prefixed_userid not in principals:
        principals = [request.prefixed_userid] + principals

    return principals


def build_request(original, dict_obj):
    """
    Transform a dict object into a :class:`pyramid.request.Request` object.

    It sets a ``parent`` attribute on the resulting request assigned with
    the `original` request specified.

    :param original: the original request.
    :param dict_obj: a dict object with the sub-request specifications.
    """
    api_prefix = "/{}".format(original.upath_info.split("/")[1])
    path = dict_obj["path"]
    if not path.startswith(api_prefix):
        path = api_prefix + path

    path = path.encode("utf-8")

    method = dict_obj.get("method") or "GET"

    headers = dict(original.headers)
    headers.update(**dict_obj.get("headers") or {})
    # Body can have different length, do not use original header.
    headers.pop("Content-Length", None)

    payload = dict_obj.get("body") or ""

    # Payload is always a dict (from ``BatchRequestSchema.body``).
    # Send it as JSON for subrequests.
    if isinstance(payload, dict):
        headers["Content-Type"] = "application/json; charset=utf-8"
        payload = json.dumps(payload)

    request = Request.blank(
        path=path.decode("latin-1"), headers=headers, POST=payload, method=method
    )
    request.registry = original.registry
    apply_request_extensions(request)

    # This is used to distinguish subrequests from direct incoming requests.
    # See :func:`kinto.core.initialization.setup_logging()`
    request.parent = original

    return request


def build_response(response, request):
    """
    Transform a :class:`pyramid.response.Response` object into a serializable
    dict.

    :param response: a response object, returned by Pyramid.
    :param request: the request that was used to get the response.
    """
    dict_obj = {}
    dict_obj["path"] = unquote(request.path)
    dict_obj["status"] = response.status_code
    dict_obj["headers"] = dict(response.headers)

    body = ""
    if request.method != "HEAD":
        # XXX : Pyramid should not have built response body for HEAD!
        try:
            body = response.json
        except ValueError:
            body = response.body
    dict_obj["body"] = body

    return dict_obj


def follow_subrequest(request, subrequest, **kwargs):
    """Run a subrequest (e.g. batch), and follow the redirection if any.

    :rtype: tuple
    :returns: the reponse and the redirection request (or `subrequest`
              if no redirection happened.)
    """
    try:
        try:
            return request.invoke_subrequest(subrequest, **kwargs), subrequest
        except Exception as e:
            resp = render_view_to_response(e, subrequest)
            if not resp or resp.status_code >= 500:
                raise e
            raise resp
    except httpexceptions.HTTPRedirection as e:
        new_location = e.headers["Location"]
        new_request = Request.blank(
            path=new_location,
            headers=subrequest.headers,
            POST=subrequest.body,
            method=subrequest.method,
        )
        new_request.bound_data = subrequest.bound_data
        new_request.parent = getattr(subrequest, "parent", None)
        return request.invoke_subrequest(new_request, **kwargs), new_request


def strip_uri_prefix(path):
    """
    Remove potential version prefix in URI.
    """
    return re.sub(r"^(/v\d+)?", "", str(path))


def view_lookup(request, uri):
    """
    A convenience method for view_lookup_registry when you have a request.

    :param request: the current request (used to obtain registry).
    :param uri: a plural or object endpoint URI.
    :rtype: tuple
    :returns: the resource name and the associated matchdict.
    """
    return view_lookup_registry(request.registry, uri)


def view_lookup_registry(registry, uri):
    """
    Look-up the specified `uri` and return the associated resource name
    along the match dict.

    :param registry: the application's registry.
    :param uri: a plural or object endpoint URI.
    :rtype: tuple
    :returns: the resource name and the associated matchdict.
    """
    api_prefix = f"/{registry.route_prefix}"
    path = api_prefix + uri

    q = registry.queryUtility
    routes_mapper = q(IRoutesMapper)

    fakerequest = Request.blank(path=path)
    info = routes_mapper(fakerequest)
    matchdict, route = info["match"], info["route"]
    if route is None:
        raise ValueError("URI has no route")

    resource_name = route.name.replace("-object", "").replace("-plural", "")
    return resource_name, matchdict


def instance_uri(request, resource_name, **params):
    """Return the URI for the given resource."""
    return strip_uri_prefix(request.route_path(f"{resource_name}-object", **params))


def instance_uri_registry(registry, resource_name, **params):
    """Return the URI for the given resource, even if you don't have a request.

    This gins up a request using Request.blank and so does not support
    any routes with pregenerators.
    """
    request = Request.blank(path="")
    request.registry = registry
    return instance_uri(request, resource_name, **params)


def apply_json_patch(obj, ops):
    """
    Apply JSON Patch operations using jsonpatch.

    :param object: base object where changes should be applied (not in-place).
    :param list changes: list of JSON patch operations.
    :param bool only_data: param to limit the scope of the patch only to 'data'.
    :returns dict data: patched object data.
             dict permissions: patched object permissions
    """
    data = {**obj}

    # Permissions should always have read and write fields defined (to allow add)
    permissions = {"read": set(), "write": set()}

    # Get permissions if available on the resource (using SharableResource)
    permissions.update(data.pop("__permissions__", {}))

    # Permissions should be mapped as a dict, since jsonpatch doesn't accept
    # sets and lists are mapped as JSON arrays (not indexed by value)
    permissions = {k: {i: i for i in v} for k, v in permissions.items()}

    resource = {"data": data, "permissions": permissions}

    # Allow patch permissions without value since key and value are equal on sets
    for op in ops:
        # 'path' is here since it was validated.
        if op["path"].startswith(("/permissions/read/", "/permissions/write/")):
            op["value"] = op["path"].split("/")[-1]

    try:
        result = jsonpatch.apply_patch(resource, ops)

    except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as e:
        raise ValueError(e)

    return result
