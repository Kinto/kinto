from pyramid.security import forget
from pyramid.view import forbidden_view_config
from pyramid.httpexceptions import HTTPForbidden, HTTPUnauthorized


@forbidden_view_config()
def authorization_required(request):
    """Distinguish authentication required (``401 Unauthorized``) from
    not allowed (``403 Forbidden``).
    """
    if not request.authenticated_userid:
        response = HTTPUnauthorized()
        response.headers.extend(forget(request))
        return response

    response = HTTPForbidden()
    return response
