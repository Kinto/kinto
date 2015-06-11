import mock
import os
import threading
import functools

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest

from cornice import errors as cornice_errors
from pyramid.url import parse_url_overrides
from pyramid.security import IAuthorizationPolicy
from zope.interface import implementer

from cliquet import DEFAULT_SETTINGS
from cliquet.storage import generators
from cliquet.tests.testapp import main as testapp

# This is the principal a connected user should have (in the tests).
USER_PRINCIPAL = ('basicauth_9f2d363f98418b13253d6d7193fc88690302'
                  'ab0ae21295521f6029dffe9dc3b0')


class DummyRequest(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.upath_info = '/v0/'
        self.registry = mock.MagicMock(settings=DEFAULT_SETTINGS)
        self.registry.id_generator = generators.UUID4()
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors(request=self)
        self.authenticated_userid = 'bob'
        self.json = {}
        self.validated = {}
        self.matchdict = {}
        self.response = mock.MagicMock(headers={})

        def route_url(*a, **kw):
            # XXX: refactor DummyRequest to take advantage of `pyramid.testing`
            parts = parse_url_overrides(kw)
            return ''.join([p for p in parts if p])

        self.route_url = route_url


def get_request_class(prefix):

    class PrefixedRequestClass(webtest.app.TestRequest):

        @classmethod
        def blank(cls, path, *args, **kwargs):
            path = '/%s%s' % (prefix, path)
            return webtest.app.TestRequest.blank(path, *args, **kwargs)

    return PrefixedRequestClass


class BaseWebTest(object):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = self._get_test_app()
        self.storage = self.app.app.registry.storage
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic bWF0OjE='
        }

    def _get_test_app(self, settings=None):
        app = webtest.TestApp(testapp(self.get_app_settings(settings)))
        app.RequestClass = get_request_class(self.api_prefix)
        return app

    def get_app_settings(self, additional_settings=None):
        settings = DEFAULT_SETTINGS.copy()
        settings['cliquet.project_name'] = 'cliquet'
        settings['cliquet.project_docs'] = 'https://cliquet.rtfd.org/'
        settings['multiauth.authorization_policy'] = (
            'cliquet.tests.support.AllowAuthorizationPolicy')

        if additional_settings is not None:
            settings.update(additional_settings)
        return settings

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()


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
        if USER_PRINCIPAL in principals:
            return True
        return False

    def principals_allowed_by_permission(self, context, permission):
        raise NotImplementedError()  # PRAGMA NOCOVER


def authorize(permits=True, authz_class=None):
    """Patch the default authorization policy to return what is specified
    in :param:permits.
    """
    if authz_class is None:
        authz_class = 'cliquet.tests.support.AllowAuthorizationPolicy'

    def wrapper(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            with mock.patch(
                    '%s.permits' % authz_class,
                    return_value=permits):
                return f(*args, **kwargs)
        return wrapped
    return wrapper

skip_if_travis = unittest.skipIf('TRAVIS' in os.environ, "travis")
