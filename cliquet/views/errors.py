from functools import wraps

from pyramid import httpexceptions
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.settings import asbool
from pyramid.security import forget, NO_PERMISSION_REQUIRED, Authenticated
from pyramid.view import (
    forbidden_view_config, notfound_view_config, view_config
)

from cliquet.errors import http_error, ERRORS
from cliquet.logs import logger
from cliquet.storage import exceptions as storage_exceptions
from cliquet.utils import reapply_cors, encode_header


def cors(view):
    """Decorator to make sure CORS headers are correctly processed."""

    @wraps(view)
    def wrap_view(request, *args, **kwargs):
        response = view(request, *args, **kwargs)

        # We need to re-apply the CORS checks done by Cornice, since we're
        # recreating the response from scratch.
        return reapply_cors(request, response)

    return wrap_view


@forbidden_view_config()
@cors
def authorization_required(request):
    """Distinguish authentication required (``401 Unauthorized``) from
    not allowed (``403 Forbidden``).
    """
    if Authenticated not in request.effective_principals:
        error_msg = "Please authenticate yourself to use this endpoint."
        response = http_error(httpexceptions.HTTPUnauthorized(),
                              errno=ERRORS.MISSING_AUTH_TOKEN,
                              message=error_msg)
        response.headers.extend(forget(request))
        return response

    error_msg = "This user cannot access this resource."
    response = http_error(httpexceptions.HTTPForbidden(),
                          errno=ERRORS.FORBIDDEN,
                          message=error_msg)
    return response


@notfound_view_config()
@cors
def page_not_found(request):
    """Return a JSON 404 error response."""
    config_key = 'trailing_slash_redirect_enabled'
    redirect_enabled = request.registry.settings[config_key]
    trailing_slash_redirection_enabled = asbool(redirect_enabled)

    querystring = request.url[(request.url.rindex(request.path) +
                               len(request.path)):]

    errno = ERRORS.MISSING_RESOURCE
    error_msg = "The resource you are looking for could not be found."

    if not request.path.startswith('/' + request.registry.route_prefix):
        errno = ERRORS.VERSION_NOT_AVAILABLE
        error_msg = ("The requested protocol version is not available "
                     "on this server.")
    elif trailing_slash_redirection_enabled:
        redirect = None

        if request.path.endswith('/'):
            path = request.path.rstrip('/')
            redirect = '%s%s' % (path, querystring)
        elif request.path == '/' + request.registry.route_prefix:
            # Case for /v0 -> /v0/
            redirect = '/%s/%s' % (request.registry.route_prefix, querystring)

        if redirect:
            return HTTPTemporaryRedirect(redirect)

    response = http_error(httpexceptions.HTTPNotFound(),
                          errno=errno,
                          message=error_msg)
    return response


@view_config(context=httpexceptions.HTTPServiceUnavailable,
             permission=NO_PERMISSION_REQUIRED)
def service_unavailable(response, request):
    if response.content_type != 'application/json':
        error_msg = ("Service temporary unavailable "
                     "due to overloading or maintenance, please retry later.")
        response = http_error(response, errno=ERRORS.BACKEND,
                              message=error_msg)

    retry_after = request.registry.settings['retry_after_seconds']
    response.headers["Retry-After"] = encode_header('%s' % retry_after)
    return reapply_cors(request, response)


@view_config(context=httpexceptions.HTTPMethodNotAllowed,
             permission=NO_PERMISSION_REQUIRED)
def method_not_allowed(context, request):
    if context.content_type == 'application/json':
        return context

    response = http_error(context,
                          errno=ERRORS.METHOD_NOT_ALLOWED,
                          message="Method not allowed on this endpoint.")
    return reapply_cors(request, response)


@view_config(context=Exception, permission=NO_PERMISSION_REQUIRED)
@view_config(context=httpexceptions.HTTPException,
             permission=NO_PERMISSION_REQUIRED)
def error(context, request):
    """Catch server errors and trace them."""
    if isinstance(context, httpexceptions.Response):
        return reapply_cors(request, context)

    if isinstance(context, storage_exceptions.BackendError):
        logger.critical(context.original, exc_info=True)
        response = httpexceptions.HTTPServiceUnavailable()
        return service_unavailable(response, request)

    logger.error(context, exc_info=True)

    error_msg = "A programmatic error occured, developers have been informed."
    info = request.registry.settings['error_info_link']
    response = http_error(httpexceptions.HTTPInternalServerError(),
                          message=error_msg,
                          info=info)

    return reapply_cors(request, response)
