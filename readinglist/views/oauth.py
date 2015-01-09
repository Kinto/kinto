import uuid

from cornice import Service
from pyramid.httpexceptions import HTTPUnauthorized, HTTPServiceUnavailable
from colander import MappingSchema, SchemaNode, String
from fxa.oauth import Client as OAuthClient
from fxa import errors as pyfxa_errors


login = Service(name='fxa-oauth-login', path='/fxa-oauth/login')
token = Service(name='fxa-oauth-token', path='/fxa-oauth/token')


fxa_conf = lambda request, name: request.registry['fxa-oauth.' + name]


def persist_state(request):
    """Persist arbitrary string in session.
    It will be compared when return from login page on OAuth server.
    """
    state = uuid.uuid4().hex
    request.response.set_cookie('state', state)
    return state


@login.get()
def fxa_oauth_login(request):
    """Helper to redirect client towards FxA login form.
    """
    state = persist_state(request)
    form_url = ('{oauth_uri}/authorization?action=signin'
                '&client_id={client_id}&state={state}&scope={scope}')
    form_url = form_url.format(oauth_uri=fxa_conf(request, 'oauth_uri'),
                               client_id=fxa_conf(request, 'client_id'),
                               scope=fxa_conf(request, 'scope'),
                               state=state)
    request.response.status = 302
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
    try:
        stored_state = request.cookies.pop('state')
    except KeyError:
        return HTTPUnauthorized()

    # Compare with previously persisted state
    if stored_state != state:
        # XXX: use Cornice errors
        request.response.status = 400
        return

    # Trade the OAuth code for a longer-lived token
    auth_client = OAuthClient(server_url=fxa_conf(request, 'oauth_uri'),
                              client_id=fxa_conf(request, 'client_id'),
                              client_secret=fxa_conf(request, 'client_secret'))
    try:
        token = auth_client.trade_code(code)
    except pyfxa_errors.OutOfProtocolError:
        return HTTPServiceUnavailable()
    except pyfxa_errors.InProtocolError:
        # XXX: use exception details
        request.response.status = 400
        return

    data = {
        'token': token,
    }
    return data
