from zope.interface import implementer
from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthenticationPolicy, IAuthorizationPolicy
from pyramid.security import Authenticated
from pyramid.httpexceptions import HTTPServiceUnavailable
from fxa.oauth import Client as OAuthClient
from fxa import errors as fxa_errors


def check_credentials(username, password, request):
    """Basic auth backdoor. Used for testing (unit and loads)
    """
    settings = request.registry.settings
    credentials = settings.get('readinglist.basic_auth_backdoor', '')
    is_matching = tuple(credentials.split(':', 1)) == (username, password)
    return [username] if is_matching else []


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

        try:
            authmeth, auth = authorization.split(' ', 1)
            assert authmeth.lower() == 'bearer'
        except (AssertionError, ValueError):
            return None

        server_url = request.registry.settings['fxa-oauth.oauth_uri']
        scope = request.registry.settings['fxa-oauth.scope']

        auth_client = OAuthClient(server_url=server_url)
        try:
            profile = auth_client.verify_token(token=auth, scope=scope)
            user_id = profile['user']
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
        return Authenticated in principals

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER
