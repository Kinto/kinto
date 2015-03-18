import uuid
from six.moves.urllib.parse import urlparse
from fnmatch import fnmatch

from cornice import Service
import colander
from fxa.oauth import Client as OAuthClient
from fxa import errors as fxa_errors

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.settings import aslist

from cliquet import logger
from cliquet import errors
from cliquet.schema import URL
from cliquet.views.errors import authorization_required
from cliquet.views.oauth import fxa_conf

login = Service(name='fxa-oauth-login',
                path='/fxa-oauth/login',
                error_handler=errors.json_error_handler)

token = Service(name='fxa-oauth-token',
                path='/fxa-oauth/token',
                error_handler=errors.json_error_handler)


def persist_state(request):
    """Persist arbitrary string in cache.
    It will be matched when the user returns from the OAuth server login
    page.
    """
    state = uuid.uuid4().hex
    redirect_url = request.validated['redirect']
    expiration = int(fxa_conf(request, 'cache_ttl_seconds'))
    request.cache.set(state, redirect_url, expiration)
    return state


class FxALoginRequest(colander.MappingSchema):
    redirect = URL(location="querystring")


def authorized_redirect(req):
    authorized = aslist(fxa_conf(req, 'webapp.authorized_domains'))
    if 'redirect' not in req.validated:
        return True

    domain = urlparse(req.validated['redirect']).netloc

    if not any((fnmatch(domain, auth) for auth in authorized)):
        req.errors.add('querystring', 'redirect',
                       'redirect URL is not authorized')


@login.get(schema=FxALoginRequest, permission=NO_PERMISSION_REQUIRED,
           validators=authorized_redirect)
def fxa_oauth_login(request):
    """Helper to redirect client towards FxA login form."""
    state = persist_state(request)
    form_url = ('{oauth_uri}/authorization?action=signin'
                '&client_id={client_id}&state={state}&scope={scope}')
    form_url = form_url.format(oauth_uri=fxa_conf(request, 'oauth_uri'),
                               client_id=fxa_conf(request, 'client_id'),
                               scope=fxa_conf(request, 'scope'),
                               state=state)
    request.response.status_code = 302
    request.response.headers['Location'] = form_url
    return {}


class OAuthRequest(colander.MappingSchema):
    code = colander.SchemaNode(colander.String(), location="querystring")
    state = colander.SchemaNode(colander.String(), location="querystring")


@token.get(schema=OAuthRequest, permission=NO_PERMISSION_REQUIRED)
def fxa_oauth_token(request):
    """Return OAuth token from authorization code.
    """
    state = request.validated['state']
    code = request.validated['code']

    # Require on-going session
    stored_redirect = request.cache.get(state)

    # Make sure we cannot try twice with the same code
    request.registry.cache.delete(state)
    if not stored_redirect:
        return authorization_required(request)

    # Trade the OAuth code for a longer-lived token
    auth_client = OAuthClient(server_url=fxa_conf(request, 'oauth_uri'),
                              client_id=fxa_conf(request, 'client_id'),
                              client_secret=fxa_conf(request, 'client_secret'))
    try:
        token = auth_client.trade_code(code)
    except fxa_errors.OutOfProtocolError:
        raise httpexceptions.HTTPServiceUnavailable()
    except fxa_errors.InProtocolError as error:
        logger.error(error)
        error_details = {
            'name': 'code',
            'location': 'querystring',
            'description': 'Firefox Account code validation failed.'
        }
        errors.raise_invalid(request, **error_details)

    return httpexceptions.HTTPFound(location='%s%s' % (stored_redirect, token))
