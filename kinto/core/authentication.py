from pyramid import authentication as base_auth

from kinto.core import utils


def prefixed_userid(request):
    """In Cliquet users ids are prefixed with the policy name that is
    contained in Pyramid Multiauth.
    If a custom authn policy is used, without authn_type, this method returns
    the user id without prefix.
    """
    # If pyramid_multiauth is used, a ``authn_type`` is set on request
    # when a policy succesfully authenticates a user.
    # (see :func:`kinto.core.initialization.setup_authentication`)
    authn_type = getattr(request, 'authn_type', None)
    if authn_type is not None:
        return authn_type + ':' + request.selected_userid


class BasicAuthAuthenticationPolicy(base_auth.BasicAuthAuthenticationPolicy):
    """Basic auth implementation.

    Allow any user with any credentials (e.g. there is no need to create an
    account).

    """
    def __init__(self, *args, **kwargs):
        def noop_check(*a):
            return []
        super(BasicAuthAuthenticationPolicy, self).__init__(noop_check,
                                                            *args,
                                                            **kwargs)

    def effective_principals(self, request):
        # Bypass default Pyramid construction of principals because
        # Pyramid multiauth already adds userid, Authenticated and Everyone
        # principals.
        return []

    def unauthenticated_userid(self, request):
        settings = request.registry.settings

        credentials = self._get_credentials(request)
        if credentials:
            username, password = credentials
            if not username:
                return

            hmac_secret = settings['userid_hmac_secret']
            credentials = '%s:%s' % credentials
            userid = utils.hmac_digest(hmac_secret, credentials)
            return userid
