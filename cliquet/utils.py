import ast
import os
import six
import time
from base64 import b64decode, b64encode
from binascii import hexlify

import ujson as json
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


def decode_token(token):
    """Take a token and return the decoded base64 JSON."""
    return json.loads(decode64(token))


def encode_token(pagination_rules):
    """Take a list of rules and return a base64-ed JSON."""
    json_rules = json.dumps(pagination_rules)
    return encode64(json_rules)


def encode64(content):
    """Encode some content in base64."""
    return b64encode(content.encode('utf-8')).decode('utf-8')


def decode64(encoded_content):
    """Decode some base64 encoded content."""
    return b64decode(encoded_content.encode('utf-8')).decode('utf-8')


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
    if request.matched_route:
        services = request.registry.cornice_services
        pattern = request.matched_route.pattern
        service = services[pattern]

        request.info['cors_checked'] = False
        response = cors.ensure_origin(service, request, response)
    return response
