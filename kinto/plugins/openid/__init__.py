from typing import Any

import jwt
import requests
from pyramid import authentication as base_auth
from pyramid.config import Configurator
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.settings import aslist
from zope.interface import implementer

from kinto.core import logger
from kinto.core import utils as core_utils
from kinto.core.openapi import OpenAPI
from kinto.core.types import Request

from .utils import fetch_openid_config


@implementer(IAuthenticationPolicy)
class OpenIDConnectPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, issuer: str, client_id: str, realm: str = "Realm", **kwargs: Any) -> None:
        self.realm = realm
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = kwargs.get("client_secret", "")
        self.audience = kwargs.get("audience", "")
        self.header_type = kwargs.get("header_type", "Bearer")
        self.userid_field = kwargs.get("userid_field", "sub")
        self.verification_ttl = int(kwargs.get("verification_ttl_seconds", 86400))

        # Fetch OpenID config (at instantiation, ie. startup)
        self.oid_config = fetch_openid_config(issuer)

        self._jwks_client: jwt.PyJWKClient | None = None

    def unauthenticated_userid(self, request: Request) -> str | None:
        """Return the userid or ``None`` if token could not be verified."""
        settings = request.registry.settings
        hmac_secret = settings["userid_hmac_secret"]

        authorization = request.headers.get("Authorization", "")
        try:
            authmeth, access_token = authorization.split(" ", 1)
        except ValueError:
            return None

        if authmeth.lower() != self.header_type.lower():
            return None

        # Check cache if this token was already verified for these provider settings.
        cache_token = f"{self.issuer}:{self.client_id}:{self.audience}:{access_token}"
        hmac_tokens = core_utils.hmac_digest(hmac_secret, cache_token)
        cache_key = f"openid:verify:{hmac_tokens}"
        payload = request.registry.cache.get(cache_key)
        if payload is None:
            # This can take some time.
            payload = self._verify_token(access_token)
            if payload is None:
                return None
        # Save for next time / refresh ttl.
        request.registry.cache.set(cache_key, payload, ttl=self.verification_ttl)
        request.bound_data["user_profile"] = payload
        # Extract meaningful field from userinfo (eg. email or sub)
        return payload.get(self.userid_field)

    def forget(self, request: Request) -> list[tuple[str, str]]:
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        return [("WWW-Authenticate", '%s realm="%s"' % (self.header_type, self.realm))]

    def _verify_token(self, access_token: str) -> Any:
        if self.audience != "" and self._decode_jwt(access_token) is None:
            # Logged debug in `_decode_jwt()`.
            return None

        uri = self.oid_config["userinfo_endpoint"]
        # Opaque access token string. Fetch user info from profile.
        try:
            resp = requests.get(uri, headers={"Authorization": "Bearer " + access_token})
            resp.raise_for_status()
            userprofile = resp.json()
            return userprofile

        except (requests.exceptions.HTTPError, ValueError, KeyError) as e:
            logger.debug("Unable to fetch user profile from %s (%s)" % (uri, e))
            return None

    def _get_jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:
            self._jwks_client = jwt.PyJWKClient(self.oid_config["jwks_uri"])
        return self._jwks_client

    def _decode_jwt(self, access_token: str) -> Any:
        try:
            signing_key = self._get_jwks_client().get_signing_key_from_jwt(access_token)
            return jwt.decode(
                access_token,
                signing_key.key,
                # Verify issuer
                issuer=self.issuer,
                # Verify audience
                audience=self.audience if self.audience != "" else None,
            )
        except jwt.PyJWTError as e:
            logger.debug("Invalid JWT access token from %s (%s)", self.issuer, e)
            return None


def get_user_profile(request: Request) -> dict[str, Any]:
    return request.bound_data.get("user_profile", {})


def includeme(config: Configurator) -> None:
    # Activate end-points.
    config.scan("kinto.plugins.openid.views")

    settings = config.get_settings()

    openid_policies = []
    for policy in aslist(settings["multiauth.policies"]):
        v = settings.get("multiauth.policy.%s.use" % policy, "")
        if v.endswith("OpenIDConnectPolicy"):
            openid_policies.append(policy)

    if len(openid_policies) == 0:
        # Do not add the capability if no policy is configured.
        return

    providers_infos = []
    for name in openid_policies:
        issuer = settings["multiauth.policy.%s.issuer" % name]
        openid_config = fetch_openid_config(issuer)

        client_id = settings["multiauth.policy.%s.client_id" % name]
        audience = settings.get("multiauth.policy.%s.audience" % name, "")
        header_type = settings.get("multiauth.policy.%s.header_type", "Bearer")

        providers_infos.append(
            {
                "name": name,
                "issuer": openid_config["issuer"],
                "auth_path": "/openid/%s/login" % name,
                "client_id": client_id,
                "audience": audience,
                "header_type": header_type,
                "userinfo_endpoint": openid_config["userinfo_endpoint"],
            }
        )

        OpenAPI.expose_authentication_method(
            name, {"type": "oauth2", "authorizationUrl": openid_config["authorization_endpoint"]}
        )

    config.add_api_capability(
        "openid",
        description="OpenID connect support.",
        url="http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html",
        providers=providers_infos,
    )
    config.add_request_method(get_user_profile, name="get_user_profile")
