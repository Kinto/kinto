import ast
import hashlib
import hmac
import os
import re
import six
import time
import warnings
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
from pyramid.request import Request, apply_request_extensions
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
    :rtype: None
    """
    for k, v in b.items():
        if isinstance(v, dict):
            merge_dicts(a.setdefault(k, {}), v)
        else:
            a.setdefault(k, v)


def random_bytes_hex(bytes_length):
    """Return a hexstring of bytes_length cryptographic-friendly random bytes.

    :param integer bytes_length: number of random bytes.
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
        except (ValueError, SyntaxError):
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
            if isinstance(d.get(field), dict):
                subvalue = dict_subset(d[field], [subfield])
                result.setdefault(field, {}).update(subvalue)
            elif field in d:
                result[field] = d[field]
        else:
            if key in d:
                result[key] = d[key]

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


def build_request(original, dict_obj):
    """
    Transform a dict object into a ``pyramid.request.Request`` object.

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
    Transform a ``pyramid.response.Response`` object into a serializable dict.

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


class DeprecatedMeta(type):
    """A metaclass to be set on deprecated classes.

    Warning will happen when class is inherited.
    """
    def __new__(meta, name, bases, attrs):
        for b in bases:
            if isinstance(b, DeprecatedMeta):
                error_msg = b.__deprecation_warning__
                warnings.warn(error_msg, DeprecationWarning, stacklevel=2)
        return super(DeprecatedMeta, meta).__new__(meta, name, bases, attrs)
