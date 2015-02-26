import six
from pyramid import httpexceptions

from cliquet.utils import Enum, json, reapply_cors


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
    BACKEND=201,
    SERVICE_DEPRECATED=202
)


def http_error(http_exception_klass, errno=None,
               code=None, error=None, message=None, info=None):
    """Return a JSON formated response matching the error protocol.

    :param http_exception_klass: See :mod:`pyramid.httpexceptions`
    :param errno: stable application-level error number (e.g. 109)
    :param code: matches the HTTP status code (e.g 400)
    :param error: string description of error type (e.g. "Bad request")
    :param message: context information (e.g. "Invalid request parameters")
    :param info: additional details (e.g. URL to error details)
    :returns: the formatted response object
    :rtype: pyramid.httpexceptions.HTTPException
    """
    body = {
        "code": code or http_exception_klass.code,
        "errno": errno or ERRORS.UNDEFINED,
        "error": error or http_exception_klass.title
    }

    if message is not None:
        body['message'] = message

    if info is not None:
        body['info'] = info

    response = http_exception_klass(body=json.dumps(body).encode("utf-8"),
                                    content_type='application/json')
    return response


def json_error_handler(errors):
    """Cornice JSON error handler, returning consistant JSON formatted errors
    from schema validation errors.

    This is meant to be used is custom services in your applications.

    .. code-block :: python

        upload = Service(name="upload", path='/upload',
                         error_handler=errors.json_error_handler)

    :warning:

        Only the first error of the list is formatted in the response.
        (c.f. protocol).
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

    response = http_error(httpexceptions.HTTPBadRequest,
                          errno=ERRORS.INVALID_PARAMETERS,
                          error='Invalid parameters',
                          message=message)
    response.status = errors.status
    response = reapply_cors(errors.request, response)
    return response


def raise_invalid(request, location='body', **kwargs):
    """Helper to raise a validation error.

    :raises: :class:`pyramid.httpexceptions.HTTPBadRequest`
    """
    request.errors.add(location, **kwargs)
    response = json_error_handler(request.errors)
    raise response
