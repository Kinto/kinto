import json
from pyramid.config import global_registries
from pyramid.httpexceptions import (
    HTTPServiceUnavailable as PyramidHTTPServiceUnavailable, HTTPError
)
from pyramid.response import Response
from readinglist.utils import Enum

ERRORS = Enum(
    MISSING_AUTH_TOKEN=104,
    INVALID_AUTH_TOKEN=105,
    BADJSON=106,
    INVALID_PARAMETERS=107,
    MISSING_PARAMETERS=108,
    INVALID_POSTED_DATA=109,
    INVALID_RESOURCE_ID=110,
    MISSING_RESOURCE=111,
    FORBIDDEN=121,
    REQUEST_TOO_LARGE=113,
    CLIENT_REACHED_CAPACITY=117,
    UNDEFINED=999,
    BACKEND=201
)


def get_formatted_error(code, errno, error, message=None, info=None):
    result = {
        "code": code,
        "errno": errno,
        "error": error
    }

    if message is not None:
        result['message'] = message

    if info is not None:
        result['info'] = info

    return json.dumps(result)


class HTTPServiceUnavailable(PyramidHTTPServiceUnavailable):
    """Return an HTTPServiceUnavailable formatted error."""

    def __init__(self, **kwargs):
        if 'body' not in kwargs:
            kwargs['body'] = get_formatted_error(
                503, ERRORS.BACKEND, "Service unavailable",
                "Service unavailable due to high load, please retry later.")

        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/json'

        if 'headers' not in kwargs:
            kwargs['headers'] = []

        settings = global_registries.last.settings
        kwargs['headers'].append(
            ("Retry-After", settings.get('readinglist.retry_after', "30"))
        )

        super(HTTPServiceUnavailable, self).__init__(**kwargs)


class _JSONError(HTTPError):
    def __init__(self, errors, status=400):
        try:
            code = int(status)
        except ValueError:
            code = int(status[:3])

        body = get_formatted_error(
            code=code, errno=ERRORS.INVALID_PARAMETERS,
            error="Invalid parameters",
            message='%(name)s in %(location)s: %(description)s' % errors[0])
        super(Response, self).__init__(body, content_type='application/json', status=status)


def json_error(errors):
    """Returns an HTTPError with the given status and message.

    The HTTP error content type is "application/json"
    """
    return _JSONError(errors, errors.status)
