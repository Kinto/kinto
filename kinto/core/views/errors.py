import logging

from pyramid import httpexceptions
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.settings import asbool
from pyramid.security import forget, NO_PERMISSION_REQUIRED, Authenticated
from pyramid.view import view_config

from kinto.core.errors import http_error, ERRORS
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.utils import reapply_cors


logger = logging.getLogger()


@view_config(context=httpexceptions.HTTPForbidden,
             permission=NO_PERMISSION_REQUIRED)
def authorization_required(response, request):
    """Distinguish authentication required (``401 Unauthorized``) from
    not allowed (``403 Forbidden``).
    """
    if Authenticated not in request.effective_principals:
        if response.content_type != "application/json":
            error_msg = "Please authenticate yourself to use this endpoint."
            response = http_error(httpexceptions.HTTPUnauthorized(),
                                  errno=ERRORS.MISSING_AUTH_TOKEN,
                                  message=error_msg)
        response.headers.extend(forget(request))
        return response

    if response.content_type != "application/json":
        error_msg = "This user cannot access this resource."
        response = http_error(httpexceptions.HTTPForbidden(),
                              errno=ERRORS.FORBIDDEN,
                              message=error_msg)
    return reapply_cors(request, response)


@view_config(context=httpexceptions.HTTPNotFound,
             permission=NO_PERMISSION_REQUIRED)
def page_not_found(response, request):
    """Return a JSON 404 error response."""
    config_key = 'trailing_slash_redirect_enabled'
    redirect_enabled = request.registry.settings[config_key]
    trailing_slash_redirection_enabled = asbool(redirect_enabled)

    querystring = request.url[(request.url.rindex(request.path) +
                               len(request.path)):]

    errno = ERRORS.MISSING_RESOURCE
    error_msg = "The resource you are looking for could not be found."

    if not request.path.startswith('/{}'.format(request.registry.route_prefix)):
        errno = ERRORS.VERSION_NOT_AVAILABLE
        error_msg = ("The requested API version is not available "
                     "on this server.")
    elif trailing_slash_redirection_enabled:
        redirect = None

        if request.path.endswith('/'):
            path = request.path.rstrip('/')
            redirect = '{}{}'.format(path, querystring)
        elif request.path == '/{}'.format(request.registry.route_prefix):
            # Case for /v0 -> /v0/
            redirect = '/{}/{}'.format(request.registry.route_prefix, querystring)

        if redirect:
            return reapply_cors(request, HTTPTemporaryRedirect(redirect))

    if response.content_type != "application/json":
        response = http_error(httpexceptions.HTTPNotFound(),
                              errno=errno,
                              message=error_msg)
    return reapply_cors(request, response)


@view_config(context=httpexceptions.HTTPServiceUnavailable,
             permission=NO_PERMISSION_REQUIRED)
def service_unavailable(response, request):
    if response.content_type != 'application/json':
        error_msg = ("Service temporary unavailable "
                     "due to overloading or maintenance, please retry later.")
        response = http_error(response, errno=ERRORS.BACKEND,
                              message=error_msg)

    retry_after = request.registry.settings['retry_after_seconds']
    response.headers["Retry-After"] = str(retry_after)
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

    if isinstance(context, storage_exceptions.IntegrityError):
        error_msg = "Integrity constraint violated, please retry."
        response = http_error(httpexceptions.HTTPConflict(),
                              errno=ERRORS.CONSTRAINT_VIOLATED,
                              message=error_msg)
        retry_after = request.registry.settings['retry_after_seconds']
        response.headers["Retry-After"] = str(retry_after)
        return reapply_cors(request, response)

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
