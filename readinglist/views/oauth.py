import uuid

from cornice import Service
from colander import MappingSchema, SchemaNode, String
from fxa.oauth import Client as OAuthClient
from fxa import errors as fxa_errors

from pyramid.httpexceptions import HTTPFound

from readinglist.errors import HTTPServiceUnavailable, json_error
from readinglist.schema import URL
from readinglist.views.errors import authorization_required
from readinglist import logger

login = Service(name='fxa-oauth-login', path='/fxa-oauth/login')
token = Service(name='fxa-oauth-token', path='/fxa-oauth/token')


def fxa_conf(request, name):
    return request.registry.settings['fxa-oauth.' + name]


def persist_state(request):
    """Persist arbitrary string in session.
    It will be compared when return from login page on OAuth server.
    """
    state = uuid.uuid4().hex
    request.registry.session.set(state, request.validated['redirect'])
    return state


class FxALoginRequest(MappingSchema):
    redirect = URL(location="querystring")


@login.get(schema=FxALoginRequest)
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


class OAuthRequest(MappingSchema):
    code = SchemaNode(String(), location="querystring")
    state = SchemaNode(String(), location="querystring")


@token.get(schema=OAuthRequest)
def fxa_oauth_token(request):
    """Return OAuth token from authorization code.
    """
    state = request.validated['state']
    code = request.validated['code']

    # Require on-going session
    stored_redirect = request.registry.session.get(state)

    if not stored_redirect:
        return authorization_required(request)

    # Trade the OAuth code for a longer-lived token
    auth_client = OAuthClient(server_url=fxa_conf(request, 'oauth_uri'),
                              client_id=fxa_conf(request, 'client_id'),
                              client_secret=fxa_conf(request, 'client_secret'))
    try:
        token = auth_client.trade_code(code)
    except fxa_errors.OutOfProtocolError:
        return HTTPServiceUnavailable()
    except fxa_errors.InProtocolError as error:
        logger.exception(error)
        request.errors.add(
            location='querystring',
            name='code',
            description='Firefox Account code validation failed.')
        raise json_error(request.errors)

    return HTTPFound(location='%s%s' % (stored_redirect, token))
