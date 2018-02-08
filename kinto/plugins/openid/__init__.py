import re

import requests
from jose import jwt
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface import implementer

from kinto.core import logger
from kinto.core import utils as core_utils
from kinto.core.openapi import OpenAPI

from .utils import fetch_openid_config


@implementer(IAuthenticationPolicy)
class OpenIDConnectPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, issuer, client_id, realm='Realm', **kwargs):
        self.realm = realm
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = kwargs.get('client_secret', '')
        self.header_type = kwargs.get('header_type', 'Bearer')
        self.userid_field = kwargs.get('userid_field', 'sub')
        self.verification_ttl = int(kwargs.get('verification_ttl_seconds', 86400))

        # Fetch OpenID config (at instantiation, ie. startup)
        self.oid_config = fetch_openid_config(issuer)

        self._jwt_keys = None

    def unauthenticated_userid(self, request):
        """Return the userid or ``None`` if token could not be verified.
        """
        settings = request.registry.settings
        hmac_secret = settings['userid_hmac_secret']

        authorization = request.headers.get('Authorization', '')
        try:
            authmeth, payload = authorization.split(' ', 1)
        except ValueError:
            return None

        if authmeth.lower() != self.header_type.lower():
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
            payload = self._verify_token(id_token, access_token)
            if payload is None:
                return None
        # Save for next time / refresh ttl.
        request.registry.cache.set(cache_key, payload, ttl=self.verification_ttl)
        # Extract meaningful field from userinfo (eg. email or sub)
        return payload.get(self.userid_field)

    def forget(self, request):
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        return [('WWW-Authenticate', '%s realm="%s"' % (self.header_type, self.realm))]

    def _verify_token(self, id_token, access_token):
        if id_token is None:
            uri = self.oid_config["userinfo_endpoint"]
            # Opaque access token string. Fetch user info from profile.
            try:
                resp = requests.get(uri, headers={"Authorization": "Bearer " + access_token})
                resp.raise_for_status()
                userprofile = resp.json()
                return userprofile

            except (requests.exceptions.HTTPError, ValueError, KeyError) as e:
                logger.debug("Unable to fetch user profile from %s with %s" % (uri, access_token))
                return None

        # A JWT token is provided.

        # Fetch keys to verify signature
        if self._jwt_keys is None:
            jwks_uri = self.oid_config["jwks_uri"]
            resp = requests.get(jwks_uri)
            self._jwt_keys = resp.json()["keys"]

        # Read JWT header.
        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except jwt.JWTError:
            logger.debug("Invalid header. Use an RS256 signed JWT Access Token")
            return None
        # Check if algorithm is supported.
        supported_algos = self.oid_config.get("id_token_signing_alg_values_supported", ["RS256"])
        if unverified_header["alg"] not in supported_algos:
            logger.debug("Invalid header. Use an %s signed JWT Access Token" % supported_algos)
            return None
        # Pick the selected key.
        rsa_key = {}
        for key in self._jwt_keys:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = core_utils.dict_subset(key, ("kty", "kid", "use", "n", "e"))
                break
        if not rsa_key:
            logger.debug("Unable to find appropriate key")
            return None
        # Verify the signature, the claims, and decode the JWT payload.
        try:
            options = None
            if access_token is None:
                options = {"verify_at_hash": False}

            payload = jwt.decode(id_token, rsa_key, algorithms=["RS256"],
                                 audience=self.client_id, issuer=self.issuer,
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

    openid_policies = []
    for k, v in settings.items():
        m = re.match('multiauth\.policy\.(.*)\.use', k)
        if m:
            print(k, v)
            if v.endswith('OpenIDConnectPolicy'):
                openid_policies.append(m.group(1))

    if len(openid_policies) == 0:
        # Do not add the capability if no policy is configured.
        return

    providers_infos = []
    for name in openid_policies:
        issuer = settings['multiauth.policy.%s.issuer' % name]
        openid_config = fetch_openid_config(issuer)

        client_id = settings['multiauth.policy.%s.client_id' % name]
        header_type = settings.get('multiauth.policy.%s.header_type', 'Bearer')

        providers_infos.append({
            'name': name,
            'issuer': openid_config['issuer'],
            'auth_path': '/openid/%s/login' % name,
            'client_id': client_id,
            'header_type': header_type,
            'userinfo_endpoint': openid_config['userinfo_endpoint'],
        })

        OpenAPI.expose_authentication_method(name, {
            "type": "oauth2",
            "authorizationUrl": openid_config['authorization_endpoint'],
        })

    config.add_api_capability(
        'openid',
        description='OpenID connect support.',
        url='http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html',
        providers=providers_infos)
