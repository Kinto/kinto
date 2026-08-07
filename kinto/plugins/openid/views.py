import base64
import urllib.parse
from typing import Any

import colander
import requests
from pyramid import httpexceptions

from kinto.core import Service
from kinto.core.cornice.validators import colander_validator
from kinto.core.errors import ERRORS, raise_invalid
from kinto.core.resource.schema import ErrorResponseSchema
from kinto.core.schema import URL
from kinto.core.types import Request
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


def provider_validator(request: Request, **kwargs: Any) -> None:
    """
    This validator verifies that the validator in URL (eg. /openid/auth0/login)
    is a configured OpenIDConnect policy.
    """
    provider = request.matchdict["provider"]
    used = request.registry.settings.get("multiauth.policy.%s.use" % provider, "")
    if not used.endswith("OpenIDConnectPolicy"):
        request.errors.add("path", "provider", "Unknown provider %r" % provider)


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
def get_login(request: Request) -> None:
    """Initiates to login dance for the specified scopes and callback URI
    using appropriate redirections."""

    # Settings.
    provider = request.matchdict["provider"]
    settings_prefix = "multiauth.policy.%s." % provider
    settings = request.registry.settings
    issuer = settings[settings_prefix + "issuer"]
    client_id = settings[settings_prefix + "client_id"]
    audience = settings.get(settings_prefix + "audience", "")
    userid_field = settings.get(settings_prefix + "userid_field")
    state_ttl = int(settings.get(settings_prefix + "state_ttl_seconds", DEFAULT_STATE_TTL_SECONDS))
    state_length = int(settings.get(settings_prefix + "state_length", DEFAULT_STATE_LENGTH))

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
    if audience != "":
        params["audience"] = audience
    redirect = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    raise httpexceptions.HTTPTemporaryRedirect(redirect)


def validate_token_querystring(node: colander.SchemaNode, value: dict) -> None:
    """Enforce that exactly one of (code, error) is present, never both."""
    has_code = "code" in value
    has_error = "error" in value

    if has_code == has_error:
        raise colander.Invalid(
            node,
            "Provide either 'state' and 'code', or 'error' and 'error_description', but not both.",
        )


class TokenQuerystringSchema(colander.MappingSchema):
    """
    Querystring schema for the token endpoint.
    """

    code = colander.SchemaNode(colander.String(), missing=colander.drop)
    state = colander.SchemaNode(colander.String())
    error = colander.SchemaNode(colander.String(), missing=colander.drop)
    error_description = colander.SchemaNode(colander.String(), missing=colander.drop)

    validator = staticmethod(validate_token_querystring)


class TokenSchema(colander.MappingSchema):
    querystring = TokenQuerystringSchema()


token = Service(name="openid_token", path="/openid/{provider}/token", description="")


@token.get(schema=TokenSchema(), validators=(colander_validator, provider_validator))
def get_token(request: Request) -> None:
    """Trades the specified code and state against access and ID tokens.
    The client is redirected to the original ``callback`` URI with the
    result in querystring."""

    # Settings.
    provider = request.matchdict["provider"]
    settings_prefix = "multiauth.policy.%s." % provider
    settings = request.registry.settings
    issuer = settings[settings_prefix + "issuer"]
    client_id = settings[settings_prefix + "client_id"]
    client_secret = settings[settings_prefix + "client_secret"]

    state = request.GET["state"]

    # If the auth server returned an error (e.g. access_denied when audience
    # is not found), forward it back to the callback URI instead of trying
    # to trade a code that was never issued.
    error = request.GET.get("error")
    if error:
        callback = request.registry.cache.delete("openid:state:" + state)
        if callback is None:
            error_details = {
                "name": "state",
                "description": "Invalid state",
                "errno": ERRORS.INVALID_AUTH_TOKEN.value,
            }
            raise_invalid(request, **error_details)
        error_params = {"error": error}
        error_description = request.GET.get("error_description")
        if error_description:
            error_params["error_description"] = error_description
        redirect = callback + urllib.parse.urlencode(error_params)
        raise httpexceptions.HTTPTemporaryRedirect(redirect)

    # Read OpenID configuration (cached by issuer)
    oid_config = fetch_openid_config(issuer)
    token_endpoint = oid_config["token_endpoint"]

    code = request.GET["code"]

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
