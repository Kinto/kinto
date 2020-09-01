import requests
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.settings import aslist
from zope.interface import implementer

from kinto.core import logger
from kinto.core import utils as core_utils
from kinto.core.openapi import OpenAPI

from .utils import fetch_openid_config


@implementer(IAuthenticationPolicy)
class OpenIDConnectPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, issuer, client_id, realm="Realm", **kwargs):
        self.realm = realm
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = kwargs.get("client_secret", "")
        self.header_type = kwargs.get("header_type", "Bearer")
        self.userid_field = kwargs.get("userid_field", "sub")
        self.verification_ttl = int(kwargs.get("verification_ttl_seconds", 86400))

        # Fetch OpenID config (at instantiation, ie. startup)
        self.oid_config = fetch_openid_config(issuer)

        self._jwt_keys = None

    def unauthenticated_userid(self, request):
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

        # XXX JWT Access token
        # https://auth0.com/docs/tokens/access-token#access-token-format

        # Check cache if these tokens were already verified.
        hmac_tokens = core_utils.hmac_digest(hmac_secret, access_token)
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

    def forget(self, request):
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        return [("WWW-Authenticate", '%s realm="%s"' % (self.header_type, self.realm))]

    def _verify_token(self, access_token):
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


def get_user_profile(request):
    return request.bound_data.get("user_profile", {})


def includeme(config):
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
        header_type = settings.get("multiauth.policy.%s.header_type", "Bearer")

        providers_infos.append(
            {
                "name": name,
                "issuer": openid_config["issuer"],
                "auth_path": "/openid/%s/login" % name,
                "client_id": client_id,
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
