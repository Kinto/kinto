from jose import jwt
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface import implementer

import requests

from kinto.core import utils as core_utils
from kinto.core.openapi import OpenAPI

from kinto.core import logger

from .utils import fetch_openid_config


@implementer(IAuthenticationPolicy)
class OpenIDConnectPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, realm='Realm'):
        self.realm = realm

        self._jwt_keys = None

    def unauthenticated_userid(self, request):
        """Return the userid or ``None`` if token could not be verified.
        """
        settings = request.registry.settings
        issuer = settings["oidc.issuer_url"]
        client_id = settings["oidc.client_id"]
        header_type = settings.get("oidc.header_type", "bearer")
        userid_field = settings.get("oidc.userid_field", "sub")
        verification_ttl = int(settings.get("oidc.verification_ttl_seconds", 86400))
        hmac_secret = settings['userid_hmac_secret']

        authorization = request.headers.get('Authorization', '')
        try:
            authmeth, payload = authorization.split(' ', 1)
        except ValueError:
            return None

        if authmeth.lower() != header_type:
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

        # Check cache if these tokens were already verified.
        hmac_tokens = core_utils.hmac_digest(hmac_secret, '{}:{}'.format(id_token, access_token))
        cache_key = "openid:verify:%s".format(hmac_tokens)
        payload = request.registry.cache.get(cache_key)
        if payload is None:
            # This can take some time.
            payload = self._verify_token(issuer, client_id, id_token, access_token)
            if payload is None:
                return None
        # Save for next time / refresh ttl.
        request.registry.cache.set(cache_key, payload, ttl=verification_ttl)
        # Extract meaningful field from userinfo (eg. email or sub)
        return payload.get(userid_field)

    def forget(self, request):
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        header_type = request.registry.settings.get("oidc.header_type", "bearer")
        return [('WWW-Authenticate', '%s realm="%s"' % (header_type, self.realm))]

    def _verify_token(self, issuer, audience, id_token, access_token):
        oid_config = fetch_openid_config(issuer)

        if id_token is None:
            uri = oid_config["userinfo_endpoint"]
            # Opaque access token string. Fetch user info from profile.
            try:
                resp = requests.get(uri, headers={"Authorization": "Bearer " + access_token})
                resp.raise_for_status()
                userprofile = resp.json()
                return userprofile
            except (requests.exceptions.HTTPError, ValueError, KeyError) as e:
                logger.debug("Unable to fetch user profile from %s with %s" % (uri, access_token))
                return None

        # JWT token is provided.
        # Verify signature
        if self._jwt_keys is None:
            jwks_uri = oid_config["jwks_uri"]
            resp = requests.get(jwks_uri)
            self._jwt_keys = resp.json()["keys"]

        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except jwt.JWTError:
            logger.debug("Invalid header. Use an RS256 signed JWT Access Token")
            return None

        supported_algos = oid_config.get("id_token_signing_alg_values_supported", ["RS256"])
        if unverified_header["alg"] not in supported_algos:
            logger.debug("Invalid header. Use an RS256 signed JWT Access Token")
            return None

        rsa_key = {}
        for key in self._jwt_keys:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = core_utils.dict_subset(key, ("kty", "kid", "use", "n", "e"))
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
            return payload

        except jwt.ExpiredSignatureError as e:
            logger.debug("Token is expired: %s" % e)
        except jwt.JWTClaimsError as e:
            logger.debug("Incorrect claims, please check the audience and issuer: %s" % e)
        except Exception as e:
            logger.exception("Unable to parse token")
        return None


def includeme(config):
    # Activate end-points.
    config.scan('kinto.plugins.openid.views')

    settings = config.get_settings()

    issuer = settings['oidc.issuer_url']
    client_id = settings['oidc.client_id']
    openid_config = fetch_openid_config(issuer)

    config.add_api_capability(
        'openid',
        description='OpenID connect support.',
        url='http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html',
        client_id=client_id,

        auth_uri='/openid/login',
        userinfo_endpoint=openid_config['userinfo_endpoint'],
    )

    OpenAPI.expose_authentication_method('openid', {
        "type": "oauth2",
        "authorizationUrl": openid_config['authorization_endpoint'],
    })
