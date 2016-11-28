import ast
import collections
import hashlib
import hmac
import jsonpatch
import os
import re
import six
import threading
import time
from base64 import b64decode, b64encode
from binascii import hexlify
from six.moves.urllib import parse as urlparse
from enum import Enum

# ujson is not installable with pypy
try:  # pragma: no cover
    import ujson as json  # NOQA

    def json_serializer(v, **kw):
        return json.dumps(v, escape_forward_slashes=False)

except ImportError:  # pragma: no cover
    import json  # NOQA

    json_serializer = json.dumps

try:
    # Register psycopg2cffi as psycopg2
    from psycopg2cffi import compat
except ImportError:  # pragma: no cover
    pass
else:  # pragma: no cover
    compat.register()

try:
    import sqlalchemy
except ImportError:  # pragma: no cover
    sqlalchemy = None

from pyramid import httpexceptions
from pyramid.interfaces import IRoutesMapper
from pyramid.request import Request, apply_request_extensions
from pyramid.security import Authenticated
from pyramid.settings import aslist
from pyramid.view import render_view_to_response
from cornice import cors
from colander import null


def strip_whitespace(v):
    """Remove whitespace, newlines, and tabs from the beginning/end
    of a string.

    :param str v: the string to strip.
    :rtype: str
    """
    return v.strip(' \t\n\r') if v is not null else v


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


def synchronized(method):
    """Class method decorator to make sure two threads do not execute some code
    at the same time (c.f Java ``synchronized`` keyword).

    The decorator installs a mutex on the class instance.
    """
    def decorated(self, *args, **kwargs):
        try:
            lock = getattr(self, '__lock__')
        except AttributeError:
            lock = threading.RLock()
            setattr(self, '__lock__', lock)

        lock.acquire()
        try:
            result = method(self, *args, **kwargs)
        finally:
            lock.release()
        return result
    return decorated


def random_bytes_hex(bytes_length):
    """Return a hexstring of bytes_length cryptographic-friendly random bytes.

    :param int bytes_length: number of random bytes.
    :rtype: str
    """
    return hexlify(os.urandom(bytes_length)).decode('utf-8')


def native_value(value):
    """Convert string value to native python values.

    :param str value: value to interprete.
    :returns: the value coerced to python type
    """
    if isinstance(value, six.string_types):
        if value.lower() in ['on', 'true', 'yes']:
            value = True
        elif value.lower() in ['off', 'false', 'no']:
            value = False
        try:
            return ast.literal_eval(value)
        except (TypeError, ValueError, SyntaxError):
            pass
    return value


def read_env(key, value):
    """Read the setting key from environment variables.

    :param key: the setting name
    :param value: default value if undefined in environment
    :returns: the value from environment, coerced to python type
    """
    envkey = key.replace('.', '_').replace('-', '_').upper()
    return native_value(os.getenv(envkey, value))


def encode64(content, encoding='utf-8'):
    """Encode some content in base64.

    :rtype: str
    """
    return b64encode(content.encode(encoding)).decode(encoding)


def decode64(encoded_content, encoding='utf-8'):
    """Decode some base64 encoded content.

    :rtype: str
    """
    return b64decode(encoded_content.encode(encoding)).decode(encoding)


def hmac_digest(secret, message, encoding='utf-8'):
    """Return hex digest of a message HMAC using secret"""
    if isinstance(secret, six.text_type):
        secret = secret.encode(encoding)
    return hmac.new(secret,
                    message.encode(encoding),
                    hashlib.sha256).hexdigest()


def dict_subset(d, keys):
    """Return a dict with the specified keys"""
    result = {}

    for key in keys:
        if '.' in key:
            field, subfield = key.split('.', 1)
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


class COMPARISON(Enum):
    LT = '<'
    MIN = '>='
    MAX = '<='
    NOT = '!='
    EQ = '=='
    GT = '>'
    IN = 'in'
    EXCLUDE = 'exclude'
    LIKE = 'like'


def reapply_cors(request, response):
    """Reapply cors headers to the new response with regards to the request.

    We need to re-apply the CORS checks done by Cornice, in case we're
    recreating the response from scratch.

    """
    service = request.current_service
    if service:
        request.info['cors_checked'] = False
        cors.apply_cors_post_request(service, request, response)
        response = cors.ensure_origin(service, request, response)
    else:
        # No existing service is concerned, and Cornice is not implied.
        origin = request.headers.get('Origin')
        if origin:
            settings = request.registry.settings
            allowed_origins = set(aslist(settings['cors_origins']))
            required_origins = {'*', decode_header(origin)}
            if allowed_origins.intersection(required_origins):
                origin = encode_header(origin)
                response.headers['Access-Control-Allow-Origin'] = origin

        # Import service here because kinto.core import utils
        from kinto.core import Service
        if Service.default_cors_headers:
            headers = ','.join(Service.default_cors_headers)
            response.headers['Access-Control-Expose-Headers'] = headers
    return response


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
    authn_type = getattr(request, 'authn_type', None)
    if authn_type is not None:
        return authn_type + ':' + request.selected_userid


def prefixed_principals(request):
    """
    :returns: the list principals with prefixed user id.
    """
    principals = request.effective_principals
    if Authenticated not in principals:
        return principals

    # Remove unprefixed user id on effective_principals to avoid conflicts.
    # (it is added via Pyramid Authn policy effective principals)
    userid = request.prefixed_userid
    if ':' in userid:
        prefix, userid = userid.split(':', 1)
    principals = [p for p in principals if p != userid]

    if request.prefixed_userid not in principals:
        principals.append(request.prefixed_userid)

    return principals


def build_request(original, dict_obj):
    """
    Transform a dict object into a :class:`pyramid.request.Request` object.

    It sets a ``parent`` attribute on the resulting request assigned with
    the `original` request specified.

    :param original: the original request.
    :param dict_obj: a dict object with the sub-request specifications.
    """
    api_prefix = '/%s' % original.upath_info.split('/')[1]
    path = dict_obj['path']
    if not path.startswith(api_prefix):
        path = api_prefix + path

    path = path.encode('utf-8')

    method = dict_obj.get('method') or 'GET'

    headers = dict(original.headers)
    headers.update(**dict_obj.get('headers') or {})
    # Body can have different length, do not use original header.
    headers.pop('Content-Length', None)

    payload = dict_obj.get('body') or ''

    # Payload is always a dict (from ``BatchRequestSchema.body``).
    # Send it as JSON for subrequests.
    if isinstance(payload, dict):
        headers['Content-Type'] = encode_header(
            'application/json; charset=utf-8')
        payload = json.dumps(payload)

    if six.PY3:  # pragma: no cover
        path = path.decode('latin-1')

    request = Request.blank(path=path,
                            headers=headers,
                            POST=payload,
                            method=method)
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
    dict_obj['path'] = urlparse.unquote(request.path)
    dict_obj['status'] = response.status_code
    dict_obj['headers'] = dict(response.headers)

    body = ''
    if request.method != 'HEAD':
        # XXX : Pyramid should not have built response body for HEAD!
        try:
            body = response.json
        except ValueError:
            body = response.body
    dict_obj['body'] = body

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
        new_location = e.headers['Location']
        new_request = Request.blank(path=new_location,
                                    headers=subrequest.headers,
                                    POST=subrequest.body,
                                    method=subrequest.method)
        new_request.bound_data = subrequest.bound_data
        new_request.parent = getattr(subrequest, 'parent', None)
        return request.invoke_subrequest(new_request, **kwargs), new_request


def encode_header(value, encoding='utf-8'):
    return _encoded(value, encoding)


def _encoded(value, encoding='utf-8'):
    """Make sure the value is of type ``str`` in both PY2 and PY3."""
    value_type = type(value)
    if value_type != str:
        # Test for Python3
        if value_type == six.binary_type:  # pragma: no cover
            value = value.decode(encoding)
        # Test for Python2
        elif value_type == six.text_type:  # pragma: no cover
            value = value.encode(encoding)
    return value


def decode_header(value, encoding='utf-8'):
    """Make sure the header is an unicode string."""
    if type(value) == six.binary_type:
        value = value.decode(encoding)
    return value


def strip_uri_prefix(path):
    """
    Remove potential version prefix in URI.
    """
    return re.sub(r'^(/v\d+)?', '', six.text_type(path))


def view_lookup(request, uri):
    """
    Look-up the specified `uri` and return the associated resource name
    along the match dict.

    :param request: the current request (used to obtain registry).
    :param uri: a plural or object endpoint URI.
    :rtype: tuple
    :returns: the resource name and the associated matchdict.
    """
    api_prefix = '/%s' % request.upath_info.split('/')[1]
    # Path should be bytes in PY2, and unicode in PY3
    path = _encoded(api_prefix + uri)

    q = request.registry.queryUtility
    routes_mapper = q(IRoutesMapper)

    fakerequest = Request.blank(path=path)
    info = routes_mapper(fakerequest)
    matchdict, route = info['match'], info['route']
    if route is None:
        raise ValueError("URI has no route")

    resource_name = route.name.replace('-record', '')\
                              .replace('-collection', '')
    return resource_name, matchdict


def instance_uri(request, resource_name, **params):
    """Return the URI for the given resource."""
    return strip_uri_prefix(request.route_path('%s-record' % resource_name,
                                               **params))


def parse_resource(resource):
    """Extract the bucket_id and collection_id of the given resource (URI)

    :param str resource: a uri formatted /buckets/<bid>/collections/<cid> or <bid>/<cid>.
    :returns: a dictionary with the bucket_id and collection_id of the resource
    """

    error_msg = "Resources should be defined as "
    "'/buckets/<bid>/collections/<cid>' or '<bid>/<cid>'. "
    "with valid collection and bucket ids."

    from kinto.views import NameGenerator
    id_generator = NameGenerator()
    parts = resource.split('/')
    if len(parts) == 2:
        bucket, collection = parts
    elif len(parts) == 5:
        _, _, bucket, _, collection = parts
    else:
        raise ValueError(error_msg)
    if bucket == '' or collection == '':
        raise ValueError(error_msg)
    if not id_generator.match(bucket) or not id_generator.match(collection):
        raise ValueError(error_msg)
    return {
        'bucket': bucket,
        'collection': collection
    }


def apply_json_patch(record, ops):
    """
    Apply JSON Patch operations using jsonpatch.

    :param record: base record where changes should be applied (not in-place).
    :param list changes: list of JSON patch operations.
    :param bool only_data: param to limit the scope of the patch only to 'data'.
    :returns dict data: patched record data.
             dict permissions: patched record permissions
    """
    data = record.copy()

    # Permissions should always have read and write fields defined (to allow add)
    permissions = {'read': set(), 'write': set()}

    # Get permissions if available on the resource (using SharableResource)
    permissions.update(data.pop('__permissions__', {}))

    # Permissions should be mapped as a dict, since jsonpatch doesn't accept
    # sets and lists are mapped as JSON arrays (not indexed by value)
    permissions = {k: {i: i for i in v} for k, v in permissions.items()}

    resource = {'data': data, 'permissions': permissions}

    # Allow patch permissions without value since key and value are equal on sets
    for op in ops:
        if 'path' in op:
            if op['path'].startswith(('/permissions/read/',
                                      '/permissions/write/')):
                op['value'] = op['path'].split('/')[-1]

    try:
        result = jsonpatch.apply_patch(resource, ops)

    except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as e:
        raise ValueError(e)

    return result
