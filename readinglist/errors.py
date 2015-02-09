import six
from pyramid.config import global_registries
from pyramid.httpexceptions import (
    HTTPServiceUnavailable as PyramidHTTPServiceUnavailable, HTTPBadRequest,
    HTTPInternalServerError as PyramidHTTPInternalServerError
)
from readinglist.utils import Enum, json


ERRORS = Enum(
    MISSING_AUTH_TOKEN=104,
    INVALID_AUTH_TOKEN=105,
    BADJSON=106,
    INVALID_PARAMETERS=107,
    MISSING_PARAMETERS=108,
    INVALID_POSTED_DATA=109,
    INVALID_RESOURCE_ID=110,
    MISSING_RESOURCE=111,
    MODIFIED_MEANWHILE=114,
    METHOD_NOT_ALLOWED=115,
    FORBIDDEN=121,
    CONSTRAINT_VIOLATED=122,
    REQUEST_TOO_LARGE=113,
    CLIENT_REACHED_CAPACITY=117,
    UNDEFINED=999,
    BACKEND=201
)


def format_error(code, errno, error, message=None, info=None):
    """Return a JSON formated string matching the error protocol."""
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
    """A HTTPServiceUnavailable formatted in JSON."""

    def __init__(self, **kwargs):
        if 'body' not in kwargs:
            kwargs['body'] = format_error(
                503, ERRORS.BACKEND, "Service unavailable",
                "Service unavailable due to high load, please retry later.")

        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/json'

        if 'headers' not in kwargs:
            kwargs['headers'] = []

        settings = global_registries.last.settings
        retry_after = settings.get(
            'readinglist.retry_after', "30").encode("utf-8")
        kwargs['headers'].append(
            ("Retry-After", retry_after)
        )

        super(HTTPServiceUnavailable, self).__init__(**kwargs)


class HTTPInternalServerError(PyramidHTTPInternalServerError):
    """A HTTPInternalServerError formatted in JSON."""

    def __init__(self, **kwargs):
        kwargs.setdefault('body', format_error(
            500,
            ERRORS.UNDEFINED,
            "Internal Server Error",
            "A programmatic error occured, developers have been informed.",
            "https://github.com/mozilla-services/readinglist/issues/"))

        kwargs.setdefault('content_type', 'application/json')

        super(HTTPInternalServerError, self).__init__(**kwargs)


def json_error(errors):
    """Return an HTTPError with the given status and message.

    The HTTP error content type is "application/json"
    """
    assert len(errors) != 0
    sorted_errors = sorted(errors, key=lambda x: six.text_type(x['name']))
    error = sorted_errors[0]
    name = error['name']
    description = error['description']

    if name is not None:
        if name in description:
            message = description
        else:
            message = '%(name)s in %(location)s: %(description)s' % error
    else:
        message = '%(location)s: %(description)s' % error

    body = format_error(
        code=400, errno=ERRORS.INVALID_PARAMETERS,
        error="Invalid parameters",
        message=message)

    response = HTTPBadRequest(body=body, content_type='application/json')
    response.status = errors.status

    raise response
