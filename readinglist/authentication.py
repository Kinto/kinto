import hashlib
import hmac

from fxa.oauth import Client as OAuthClient
from fxa import errors as fxa_errors
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy, IAuthorizationPolicy
from pyramid.security import Authenticated
from zope.interface import implementer

from readinglist.errors import HTTPServiceUnavailable


def check_credentials(username, password, request):
    """Basic auth backdoor.

    Here to ease client development to bypass FxA authentication during first
    iteration.
    """
    settings = request.registry.settings
    is_enabled = settings.get('readinglist.basic_auth_backdoor')

    if not is_enabled or not username:
        return

    hmac_secret = settings.get(
        'readinglist.userid_hmac_secret').encode('utf-8')
    credentials = '%s:%s' % (username, password)
    userid = hmac.new(hmac_secret,
                      credentials.encode('utf-8'),
                      hashlib.sha256).hexdigest()

    return ["basicauth_%s" % userid]


class BasicAuthAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    def __init__(self, *args, **kwargs):
        super(BasicAuthAuthenticationPolicy, self).__init__(check_credentials,
                                                            *args,
                                                            **kwargs)


@implementer(IAuthenticationPolicy)
class Oauth2AuthenticationPolicy(base_auth.CallbackAuthenticationPolicy):
    def __init__(self, realm='Realm'):
        self.realm = realm

    def unauthenticated_userid(self, request):
        user_id = self._get_credentials(request)
        return user_id

    def forget(self, request):
        """A no-op. Credentials are sent on every request.
        Return WWW-Authenticate Realm header for Bearer token.
        """
        return [('WWW-Authenticate', 'Bearer realm="%s"' % self.realm)]

    def _get_credentials(self, request):
        authorization = request.headers.get('Authorization', '')
        settings = request.registry.settings

        try:
            authmeth, auth = authorization.split(' ', 1)
            assert authmeth.lower() == 'bearer'
        except (AssertionError, ValueError):
            return None

        server_url = settings['fxa-oauth.oauth_uri']
        scope = settings['fxa-oauth.scope']

        auth_client = OAuthClient(server_url=server_url)
        try:
            profile = auth_client.verify_token(token=auth, scope=scope)
            hmac_secret = settings.get('readinglist.userid_hmac_secret')
            user_id = hmac.new(hmac_secret.encode('utf-8'),
                               profile['user'].encode('utf-8'),
                               hashlib.sha256).hexdigest()
        except fxa_errors.OutOfProtocolError:
            raise HTTPServiceUnavailable()
        except (fxa_errors.InProtocolError, fxa_errors.TrustError):
            return None
        return user_id


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        """Currently we don't check scopes nor permissions.
        Authenticated users only are allowed.
        """
        PERMISSIONS = {
            'readonly': Authenticated,
            'readwrite': Authenticated,
        }
        role = PERMISSIONS.get(permission)
        return role and role in principals

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER
