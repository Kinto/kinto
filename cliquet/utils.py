import ast
import hashlib
import hmac
import os
import six
import time
from base64 import b64decode, b64encode
from binascii import hexlify

import ujson as json  # NOQA
from cornice import cors
from colander import null


def strip_whitespace(v):
    """Remove whitespace, newlines, and tabs from the beginning/end
    of a string.
    """
    return v.strip(' \t\n\r') if v is not null else v


def msec_time():
    """Return current epoch time in milliseconds."""
    return int(time.time() * 1000.0)  # floor


def classname(obj):
    """Get a classname from a class."""
    return obj.__class__.__name__.lower()


def merge_dicts(a, b):
    """Merge b into a recursively, without overwriting values."""
    for k, v in b.items():
        if isinstance(v, dict):
            merge_dicts(a.setdefault(k, {}), v)
        else:
            a.setdefault(k, v)


def random_bytes_hex(bytes_length):
    """Return a hexstring of bytes_length cryptographic-friendly random bytes.
    """
    return hexlify(os.urandom(bytes_length)).decode('utf-8')


def native_value(value):
    """Convert string value to native python values."""
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
    """Encode some content in base64."""
    return b64encode(content.encode(encoding)).decode(encoding)


def decode64(encoded_content, encoding='utf-8'):
    """Decode some base64 encoded content."""
    return b64decode(encoded_content.encode(encoding)).decode(encoding)


def hmac_digest(secret, message, encoding='utf-8'):
    """Return hex digest of a message HMAC using secret"""
    return hmac.new(secret.encode(encoding),
                    message.encode(encoding),
                    hashlib.sha256).hexdigest()


def Enum(**enums):
    return type('Enum', (), enums)


COMPARISON = Enum(
    LT='<',
    MIN='>=',
    MAX='<=',
    NOT='!=',
    EQ='==',
    GT='>',
)


def reapply_cors(request, response):
    """Reapply cors headers to the new response with regards to the request.

    We need to re-apply the CORS checks done by Cornice, in case we're
    recreating the response from scratch.

    """
    service = current_service(request)
    if service:
        request.info['cors_checked'] = False
        response = cors.ensure_origin(service, request, response)
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
