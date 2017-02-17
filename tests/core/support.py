import mock
import functools

from pyramid.security import IAuthorizationPolicy, Authenticated, Everyone
from zope.interface import implementer

from kinto.core.authorization import PRIVATE
from kinto.core import testing

from .testapp import main as testapp


# This is the principal a connected user should have (in the tests).
USER_PRINCIPAL = 'basicauth:8a931a10fc88ab2f6d1cc02a07d3a81b5d4768f6f13e85c5' \
                 'd8d4180419acb1b4'


class BaseWebTest(testing.BaseWebTest):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"
    entry_point = testapp
    principal = USER_PRINCIPAL

    authorization_policy = 'tests.core.support.AllowAuthorizationPolicy'
    collection_url = '/mushrooms'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers.update(testing.get_user_headers('mat'))

    def get_app_settings(self, extras=None):
        if extras is None:
            extras = {}
        extras.setdefault('project_name', 'myapp')
        extras.setdefault('project_version', '0.0.1')
        extras.setdefault('http_api_version', '0.1')
        extras.setdefault('project_docs', 'https://kinto.readthedocs.io/')
        extras.setdefault('multiauth.authorization_policy',
                          self.authorization_policy)
        return super().get_app_settings(extras)

    def get_item_url(self, id=None):
        """Return the URL of the item using self.item_url."""
        if id is None:
            id = self.record['id']
        return '{}/{}'.format(self.collection_url, id)


@implementer(IAuthorizationPolicy)
class AllowAuthorizationPolicy:
    def permits(self, context, principals, permission):
        if permission == PRIVATE:
            return Authenticated in principals
        if Everyone in principals:
            return True
        # Kinto-Core default authz policy uses prefixed_userid.
        prefixed = [context.prefixed_userid]
        return USER_PRINCIPAL in (principals + prefixed)

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER


def authorize(permits=True, authz_class=None):
    """Patch the default authorization policy to return what is specified
    in :param:permits.
    """
    if authz_class is None:
        authz_class = 'tests.core.support.AllowAuthorizationPolicy'

    def wrapper(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            with mock.patch(
                    '{}.permits'.format(authz_class),
                    return_value=permits):
                return f(*args, **kwargs)
        return wrapped
    return wrapper
