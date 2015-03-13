import json

import ast
import os
import six
import time
from base64 import b64decode, b64encode
from binascii import hexlify

import structlog
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
        if value.lower() in ['on', 'true', 'yes', '1']:
            value = True
        elif value.lower() in ['off', 'false', 'no', '0']:
            value = False
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass
    return value


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
        service = services.get(pattern, None)

        request.info['cors_checked'] = False
        response = cors.ensure_origin(service, request, response)
    return response


class MozillaHekaRenderer(structlog.processors.JSONRenderer):
    """Build structured log entries as expected by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    """

    ENV_VERSION = '2.0'

    def __init__(self, settings):
        super(MozillaHekaRenderer, self).__init__()
        self.appname = settings.get('cliquet.project_name')
        self.hostname = os.uname()[1]  # XXX + read env or conf
        self.pid = os.getpid()

    def __call__(self, logger, name, event_dict):
        SYSLOG_LEVELS = {
            'critical': 0,
            'fatal': 0,
            'exception': 2,
            'error': 2,
            'warning': 4,
            'info': 6,
            'debug': 7,
        }
        severity = SYSLOG_LEVELS[name]

        MSEC_TO_NANOSEC = 1000000
        timestamp = msec_time() * MSEC_TO_NANOSEC

        event = event_dict.pop('event', '')

        defaults = {
            'Timestamp': timestamp,
            'Logger': self.appname,
            'Type': event,
            'Hostname': self.hostname,
            'Severity': severity,
            'Pid': self.pid,
            'EnvVersion': self.ENV_VERSION,
            'Fields': {}
        }

        for f, v in defaults.items():
            event_dict.setdefault(f, v)

        fields = [k for k in event_dict.keys() if k not in defaults]
        for f in fields:
            event_dict['Fields'][f] = event_dict.pop(f)

        return super(MozillaHekaRenderer, self).__call__(logger,
                                                         name,
                                                         event_dict)
