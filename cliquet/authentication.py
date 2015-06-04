from pyramid import authentication as base_auth
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.security import Authenticated
from zope.interface import implementer

from cliquet import utils


class BasicAuthAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    """Basic auth implementation.

    Allow any user with any credentials (e.g. there is no need to create an
    account).

    """
    def __init__(self, *args, **kwargs):
        noop_check = lambda *a: []  # NOQA
        super(BasicAuthAuthenticationPolicy, self).__init__(noop_check,
                                                            *args,
                                                            **kwargs)

    def unauthenticated_userid(self, request):
        settings = request.registry.settings

        credentials = self._get_credentials(request)
        if credentials:
            username, password = credentials
            if not username:
                return

            hmac_secret = settings['cliquet.userid_hmac_secret']
            credentials = '%s:%s' % credentials
            userid = utils.hmac_digest(hmac_secret, credentials)
            return "basicauth_%s" % userid


@implementer(IAuthorizationPolicy)
class AuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        """Currently we don't check scopes nor permissions.
        Authenticated users only are allowed.
        """
        # XXX: todo once context is build.
        # object_id = context.object_id
        # user_id = context.user_id
        # get_bound_permissions = context.get_bound_permissions
        # has_permission = context.permission.has_permission
        # return has_permission(object_id, permission, user_id,
        #                       get_bound_permissions)

        PERMISSIONS = {
            'readonly': Authenticated,
            'readwrite': Authenticated,
        }
        role = PERMISSIONS.get(permission)
        return role and role in principals

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER
