from pyramid import authentication as base_auth

from kinto.core import utils


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


def includeme(config):
    config.add_api_capability(
        "basicauth",
        description="Very basic authentication sessions. Not for production use.",
        url="http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html",
    )
