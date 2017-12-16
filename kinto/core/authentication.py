from jose import jwt
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface import implementer

import requests

from kinto.core import utils
from kinto.core.openapi import OpenAPI

from kinto.core import logger


class BasicAuthAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    """Basic auth implementation.

    Allow any user with any credentials (e.g. there is no need to create an
    account).

    """
    def __init__(self, *args, **kwargs):
        def noop_check(*a):
            return []
        super().__init__(noop_check, *args, **kwargs)

    def effective_principals(self, request):
        # Bypass default Pyramid construction of principals because
        # Pyramid multiauth already adds userid, Authenticated and Everyone
        # principals.
        return []

    def unauthenticated_userid(self, request):
        settings = request.registry.settings

        credentials = base_auth.extract_http_basic_credentials(request)
        if credentials:
            username, password = credentials
            if not username:
                return

            hmac_secret = settings['userid_hmac_secret']
            credentials = '{}:{}'.format(*credentials)
            userid = utils.hmac_digest(hmac_secret, credentials)
            return userid


@implementer(IAuthenticationPolicy)
class OpenIDConnectPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, realm='Realm'):
        self.realm = realm
        self._cache = None

        self._jwt_keys = None

    def unauthenticated_userid(self, request):
        """Return the FxA userid or ``None`` if token could not be verified.
        """
        authorization = request.headers.get('Authorization', '')
        try:
            authmeth, payload = authorization.split(' ', 1)
        except ValueError:
            return None

        if authmeth.lower() != 'bearer+oidc':
            return None

        try:
            # Bearer+OIDC id_token=jwt, access_token=bearer
            parts = payload.split(',')
            credentials = {k: v for k, v in [p.strip().split("=") for p in parts]}
            id_token = credentials["id_token"]
            access_token = credentials["access_token"]
        except (ValueError, KeyError):
            # Bearer+OIDC jwt
            id_token = payload
            access_token = None

        return self._verify_token(request, id_token, access_token)

    def forget(self, request):
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        return [('WWW-Authenticate', 'Bearer+OIDC realm="%s"' % self.realm)]

    def _verify_token(self, request, id_token, access_token):
        # Verify signature
        audience = request.registry.settings["oidc.audience"]
        issuer = request.registry.settings["oidc.issuer_url"]

        if self._jwt_keys is None:
            resp = requests.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
            jwks_uri = resp.json()["jwks_uri"]
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
    config.add_api_capability(
        'basicauth',
        description='Very basic authentication sessions. Not for production use.',
        url='http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html',
    )
    OpenAPI.expose_authentication_method('basicauth', {'type': 'basic'})
