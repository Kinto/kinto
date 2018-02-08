import urllib.parse

import colander
import requests
from pyramid import httpexceptions

from cornice.validators import colander_validator
from kinto.core import Service
from kinto.core.errors import raise_invalid, ERRORS
from kinto.core.utils import random_bytes_hex
from kinto.core.schema import URL

from .utils import fetch_openid_config


DEFAULT_STATE_TTL_SECONDS = 3600


class LoginQuerystring(colander.MappingSchema):
    callback = URL()
    scope = colander.SchemaNode(colander.String())


class LoginSchema(colander.MappingSchema):
    querystring = LoginQuerystring()


login = Service(name='openid_login',
                path='/openid/login',
                description='Initiate the OAuth2 login')


@login.get(schema=LoginSchema(), validators=(colander_validator,))
def get_login(request):
    # Settings.
    issuer = request.registry.settings["oidc.issuer_url"]
    client_id = request.registry.settings["oidc.client_id"]
    state_ttl = int(request.registry.settings.get("oidc.state_ttl_seconds",
                                                  DEFAULT_STATE_TTL_SECONDS))

    # Read OpenID configuration (cached by issuer)
    oid_config = fetch_openid_config(issuer)
    auth_endpoint = oid_config["authorization_endpoint"]

    scope = request.GET['scope']
    callback = request.GET['callback']

    # Generate a random string as state.
    # And save it until code is traded.
    state = random_bytes_hex(256)
    request.registry.cache.set("openid:state:" + state, callback, ttl=state_ttl)

    # Redirect the client to the Identity Provider that will eventually redirect
    # to the OpenID token endpoint.
    token_uri = request.route_url('openid_token') + '?'
    params = dict(client_id=client_id, response_type="code", scope=scope,
                  redirect_uri=token_uri, state=state)
    redirect = "{}?{}".format(auth_endpoint, urllib.parse.urlencode(params))
    raise httpexceptions.HTTPTemporaryRedirect(redirect)


class TokenQuerystring(colander.MappingSchema):
    code = colander.SchemaNode(colander.String())
    state = colander.SchemaNode(colander.String())


class TokenSchema(colander.MappingSchema):
    querystring = TokenQuerystring()


token = Service(name='openid_token',
                path='/openid/token',
                description='')


@token.get(schema=TokenSchema(), validators=(colander_validator,))
def get_token(request):
    # Settings.
    issuer = request.registry.settings["oidc.issuer_url"]
    client_id = request.registry.settings["oidc.client_id"]
    client_secret = request.registry.settings["oidc.client_secret"]

    # Read OpenID configuration (cached by issuer)
    oid_config = fetch_openid_config(issuer)
    token_endpoint = oid_config["token_endpoint"]

    code = request.GET["code"]
    state = request.GET["state"]

    # State can be used only once.
    callback = request.registry.cache.delete("openid:state:" + state)
    if callback is None:
        error_details = {
            'name': 'state',
            'description': 'Invalid state',
            'errno': ERRORS.INVALID_AUTH_TOKEN,
        }
        raise_invalid(request, **error_details)

    # Trade the code for tokens on the Identity Provider.
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': request.route_url('openid_token') + '?',  # required by Google Identity
        'grant_type': 'authorization_code'
    }
    resp = requests.post(token_endpoint, data=data)

    # The IdP response is forwarded to the client in the querystring/location hash.
    # (eg. callback=`http://localhost:3000/#tokens=`)
    redirect = callback + urllib.parse.quote(resp.text)
    raise httpexceptions.HTTPTemporaryRedirect(redirect)
