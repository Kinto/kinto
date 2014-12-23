from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthorizationPolicy
from zope.interface import implementer


def check_credentials(username, password, request):
    """Basic auth backdoor. Used for testing (unit and loads)
    """
    credentials = request.registry.settings['readinglist.basic_auth_backdoor']
    is_matching = tuple(credentials.split(':', 1)) == (username, password)
    return [username] if is_matching else []


class BasicAuthAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    def __init__(self, *args, **kwargs):
        super(BasicAuthAuthenticationPolicy, self).__init__(check_credentials,
                                                            *args,
                                                            **kwargs)


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        return permission in principals

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER
