import base64
import urllib.parse

import colander
import requests
from cornice.validators import colander_validator
from pyramid import httpexceptions

from kinto.core import Service
from kinto.core.errors import ERRORS, raise_invalid
from kinto.core.resource.schema import ErrorResponseSchema
from kinto.core.schema import URL
from kinto.core.utils import random_bytes_hex

from .utils import fetch_openid_config

DEFAULT_STATE_TTL_SECONDS = 3600
DEFAULT_STATE_LENGTH = 32


class RedirectHeadersSchema(colander.MappingSchema):
    """Redirect response headers."""

    location = colander.SchemaNode(colander.String(), name="Location")


class RedirectResponseSchema(colander.MappingSchema):
    """Redirect response schema."""

    headers = RedirectHeadersSchema()


response_schemas = {
    "307": RedirectResponseSchema(description="Successful redirection."),
    "400": ErrorResponseSchema(description="The request is invalid."),
}


def provider_validator(request, **kwargs):
    """
    This validator verifies that the validator in URL (eg. /openid/auth0/login)
    is a configured OpenIDConnect policy.
    """
    provider = request.matchdict["provider"]
    used = request.registry.settings.get("multiauth.policy.%s.use" % provider, "")
    if not used.endswith("OpenIDConnectPolicy"):
        request.errors.add("path", "provider", "Unknow provider %r" % provider)


class LoginQuerystringSchema(colander.MappingSchema):
    """
    Querystring schema for the login endpoint.
    """

    callback = URL()
    scope = colander.SchemaNode(colander.String())
    prompt = colander.SchemaNode(
        colander.String(), validator=colander.Regex("none"), missing=colander.drop
    )


class LoginSchema(colander.MappingSchema):
    querystring = LoginQuerystringSchema()


login = Service(
    name="openid_login", path="/openid/{provider}/login", description="Initiate the OAuth2 login"
)


@login.get(
    schema=LoginSchema(),
    validators=(colander_validator, provider_validator),
    response_schemas=response_schemas,
)
def get_login(request):
    """Initiates to login dance for the specified scopes and callback URI
    using appropriate redirections."""

    # Settings.
    provider = request.matchdict["provider"]
    settings_prefix = "multiauth.policy.%s." % provider
    issuer = request.registry.settings[settings_prefix + "issuer"]
    client_id = request.registry.settings[settings_prefix + "client_id"]
    userid_field = request.registry.settings.get(settings_prefix + "userid_field")
    state_ttl = int(
        request.registry.settings.get(
            settings_prefix + "state_ttl_seconds", DEFAULT_STATE_TTL_SECONDS
        )
    )
    state_length = int(
        request.registry.settings.get(settings_prefix + "state_length", DEFAULT_STATE_LENGTH)
    )

    # Read OpenID configuration (cached by issuer)
    oid_config = fetch_openid_config(issuer)
    auth_endpoint = oid_config["authorization_endpoint"]

    scope = request.GET["scope"]
    callback = request.GET["callback"]
    prompt = request.GET.get("prompt")

    # Check that email scope is requested if userid field is configured as email.
    if userid_field == "email" and "email" not in scope:
        error_details = {
            "name": "scope",
            "description": "Provider %s requires 'email' scope" % provider,
        }
        raise_invalid(request, **error_details)

    # Generate a random string as state.
    # And save it until code is traded.
    state = random_bytes_hex(state_length)
    request.registry.cache.set("openid:state:" + state, callback, ttl=state_ttl)

    # Redirect the client to the Identity Provider that will eventually redirect
    # to the OpenID token endpoint.
    token_uri = request.route_url("openid_token", provider=provider)
    params = dict(
        client_id=client_id, response_type="code", scope=scope, redirect_uri=token_uri, state=state
    )
    if prompt:
        # The 'prompt' parameter is optional.
        params["prompt"] = prompt
    redirect = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    raise httpexceptions.HTTPTemporaryRedirect(redirect)


class TokenQuerystringSchema(colander.MappingSchema):
    """
    Querystring schema for the token endpoint.
    """

    code = colander.SchemaNode(colander.String())
    state = colander.SchemaNode(colander.String())


class TokenSchema(colander.MappingSchema):
    querystring = TokenQuerystringSchema()


token = Service(name="openid_token", path="/openid/{provider}/token", description="")


@token.get(schema=TokenSchema(), validators=(colander_validator, provider_validator))
def get_token(request):
    """Trades the specified code and state against access and ID tokens.
    The client is redirected to the original ``callback`` URI with the
    result in querystring."""

    # Settings.
    provider = request.matchdict["provider"]
    settings_prefix = "multiauth.policy.%s." % provider
    issuer = request.registry.settings[settings_prefix + "issuer"]
    client_id = request.registry.settings[settings_prefix + "client_id"]
    client_secret = request.registry.settings[settings_prefix + "client_secret"]

    # Read OpenID configuration (cached by issuer)
    oid_config = fetch_openid_config(issuer)
    token_endpoint = oid_config["token_endpoint"]

    code = request.GET["code"]
    state = request.GET["state"]

    # State can be used only once.
    callback = request.registry.cache.delete("openid:state:" + state)
    if callback is None:
        error_details = {
            "name": "state",
            "description": "Invalid state",
            "errno": ERRORS.INVALID_AUTH_TOKEN.value,
        }
        raise_invalid(request, **error_details)

    # Trade the code for tokens on the Identity Provider.
    # Google Identity requires to specify again redirect_uri.
    redirect_uri = request.route_url("openid_token", provider=provider)
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = requests.post(token_endpoint, data=data)

    # The IdP response is forwarded to the client in the querystring/location hash.
    # (eg. callback=`http://localhost:3000/#tokens=`)
    token_info = resp.text.encode("utf-8")
    encoded_token = base64.b64encode(token_info)
    redirect = callback + urllib.parse.quote(encoded_token.decode("utf-8"))
    raise httpexceptions.HTTPTemporaryRedirect(redirect)
