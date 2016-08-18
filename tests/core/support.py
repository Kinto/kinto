import mock
import threading
import functools

import webtest
from pyramid.security import IAuthorizationPolicy, Authenticated, Everyone
from zope.interface import implementer

from kinto.core import DEFAULT_SETTINGS
from kinto.core.authorization import PRIVATE
from kinto.core.testing import get_request_class

from .testapp import main as testapp


# This is the principal a connected user should have (in the tests).
USER_PRINCIPAL = ('basicauth:9f2d363f98418b13253d6d7193fc88690302'
                  'ab0ae21295521f6029dffe9dc3b0')


class BaseWebTest(object):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"
    authorization_policy = 'tests.core.support.AllowAuthorizationPolicy'
    collection_url = '/mushrooms'
    principal = USER_PRINCIPAL

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = self.make_app()
        self.storage = self.app.app.registry.storage
        self.cache = self.app.app.registry.cache
        self.permission = self.app.app.registry.permission
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic bWF0OjE='
        }

    def make_app(self, settings=None, config=None):
        wsgi_app = testapp(self.get_app_settings(settings), config=config)
        app = webtest.TestApp(wsgi_app)
        app.RequestClass = get_request_class(self.api_prefix)
        return app

    def get_app_settings(self, additional_settings=None):
        settings = DEFAULT_SETTINGS.copy()

        settings['storage_backend'] = 'kinto.core.storage.memory'
        settings['cache_backend'] = 'kinto.core.cache.memory'
        settings['permission_backend'] = 'kinto.core.permission.memory'

        settings['project_name'] = 'myapp'
        settings['project_version'] = '0.0.1'
        settings['project_docs'] = 'https://kinto.readthedocs.io/'
        settings['multiauth.authorization_policy'] = self.authorization_policy

        if additional_settings is not None:
            settings.update(additional_settings)
        return settings

    def get_item_url(self, id=None):
        """Return the URL of the item using self.item_url."""
        if id is None:
            id = self.record['id']
        return self.collection_url + '/' + str(id)

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()
        self.cache.flush()
        self.permission.flush()


class ThreadMixin(object):

    def setUp(self):
        super(ThreadMixin, self).setUp()
        self._threads = []

    def tearDown(self):
        super(ThreadMixin, self).tearDown()

        for thread in self._threads:
            thread.join()

    def _create_thread(self, *args, **kwargs):
        thread = threading.Thread(*args, **kwargs)
        self._threads.append(thread)
        return thread


@implementer(IAuthorizationPolicy)
class AllowAuthorizationPolicy(object):
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
                    '%s.permits' % authz_class,
                    return_value=permits):
                return f(*args, **kwargs)
        return wrapped
    return wrapper
