from jose import jwt
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface import implementer

import requests

from kinto.core import utils
from kinto.core.openapi import OpenAPI

from kinto.core import logger


def fetch_openid_config(issuer):
    resp = requests.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
    return resp.json()


@implementer(IAuthenticationPolicy)
class OpenIDConnectPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, realm='Realm', prefix='bearer+oidc'):
        self.realm = realm
        self.prefix = prefix

        self._openid_config = None
        self._jwt_keys = None

    def unauthenticated_userid(self, request):
        """Return the userid or ``None`` if token could not be verified.
        """
        audience = request.registry.settings["oidc.audience"]
        issuer = request.registry.settings["oidc.issuer_url"]

        authorization = request.headers.get('Authorization', '')
        try:
            authmeth, payload = authorization.split(' ', 1)
        except ValueError:
            return None

        if authmeth.lower() != self.prefix.lower():
            return None

        try:
            # Bearer+OIDC id_token=jwt, access_token=bearer
            parts = payload.split(',')
            credentials = {k: v for k, v in [p.strip().split("=") for p in parts]}
            id_token = credentials["id_token"]
            access_token = credentials["access_token"]
        except (ValueError, KeyError):
            parts = payload.split('.')
            if len(parts) == 3:
                # Bearer+OIDC JWT ID ?
                id_token = payload
                access_token = None
            else:
                # Bearer+OIDC accesstoken
                id_token = None
                access_token = payload

            # XXX JWT Access token
            # https://auth0.com/docs/tokens/access-token#access-token-format

        return self._verify_token(issuer, audience, id_token, access_token)

    def forget(self, request):
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        return [('WWW-Authenticate', '%s realm="%s"' % (self.prefix, self.realm))]

    def _verify_token(self, issuer, audience, id_token, access_token):
        if self._openid_config is None:
            self._openid_config = fetch_openid_config(issuer)

        if id_token is None:
            uri = self._openid_config["userinfo_endpoint"]
            # Opaque access token string. Fetch user info from profile.
            try:
                resp = requests.get(uri, headers={"Authorization": "Bearer " + access_token})
                resp.raise_for_status()
                userprofile = resp.json()
                return userprofile["sub"]
            except (requests.exceptions.HTTPError, KeyError) as e:
                logger.debug("Unable to fetch user profile from %s with %s" (uri, access_token))
                return None

        # JWT token is provided.
        # Verify signature
        if self._jwt_keys is None:
            jwks_uri = self._openid_config["jwks_uri"]
            resp = requests.get(jwks_uri)
            self._jwt_keys = resp.json()["keys"]

        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except jwt.JWTError:
            logger.debug("Invalid header. Use an RS256 signed JWT Access Token")
            return None

        if unverified_header["alg"] != "RS256":
            logger.debug("Invalid header. Use an RS256 signed JWT Access Token")
            return None

        rsa_key = {}
        for key in self._jwt_keys:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = utils.dict_subset(key, ("kty", "kid", "use", "n", "e"))
                break
        if not rsa_key:
            logger.debug("Unable to find appropriate key")
            return None
        try:
            options = None
            if access_token is None:
                options = {"verify_at_hash": False}

            payload = jwt.decode(id_token, rsa_key, algorithms=["RS256"],
                                 audience=audience, issuer=issuer,
                                 options=options, access_token=access_token)
            return payload["sub"]

        except jwt.ExpiredSignatureError as e:
            logger.debug("Token is expired: %s" % e)
        except jwt.JWTClaimsError as e:
            logger.debug("Incorrect claims, please check the audience and issuer: %s" % e)
        except Exception as e:
            logger.exception("Unable to parse token")
        return None


def includeme(config):
    issuer = config.registry.settings['oidc.issuer_url']
    openid_config = fetch_openid_config(issuer)

    config.add_api_capability(
        'openid',
        description='OpenID connect support.',
        url='http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html',
        **openid_config
    )

    OpenAPI.expose_authentication_method('openid', {
        "type": "oauth2",
        "authorizationUrl": openid_config['authorization_endpoint'],
        # "flow": "implicit",
        # "scopes": {
        #   "write:pets": "modify pets in your account",
        #   "read:pets": "read your pets"
        # }
    })
