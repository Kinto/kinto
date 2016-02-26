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
from pyramid.security import IAuthorizationPolicy, Authenticated, Everyone
from zope.interface import implementer
from enum import Enum

from cliquet import DEFAULT_SETTINGS
from cliquet.authorization import PRIVATE
from cliquet.storage import generators
from cliquet.tests.testapp import main as testapp
from cliquet.utils import sqlalchemy, follow_subrequest

# This is the principal a connected user should have (in the tests).
USER_PRINCIPAL = ('basicauth:9f2d363f98418b13253d6d7193fc88690302'
                  'ab0ae21295521f6029dffe9dc3b0')


class DummyRequest(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.upath_info = '/v0/'
        self.registry = mock.MagicMock(settings=DEFAULT_SETTINGS.copy())
        self.registry.id_generator = generators.UUID4()
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors(request=self)
        self.authenticated_userid = 'bob'
        self.authn_type = 'basicauth'
        self.prefixed_userid = 'basicauth:bob'
        self.json = {}
        self.validated = {}
        self.matchdict = {}
        self.response = mock.MagicMock(headers={})

        def route_url(*a, **kw):
            # XXX: refactor DummyRequest to take advantage of `pyramid.testing`
            parts = parse_url_overrides(kw)
            return ''.join([p for p in parts if p])

        self.route_url = route_url

    follow_subrequest = follow_subrequest


def get_request_class(prefix):

    class PrefixedRequestClass(webtest.app.TestRequest):

        @classmethod
        def blank(cls, path, *args, **kwargs):
            if prefix:
                path = '/%s%s' % (prefix, path)
            return webtest.app.TestRequest.blank(path, *args, **kwargs)

    return PrefixedRequestClass


class BaseWebTest(object):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"
    authorization_policy = 'cliquet.tests.support.AllowAuthorizationPolicy'
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

        settings['storage_backend'] = 'cliquet.storage.redis'
        settings['cache_backend'] = 'cliquet.cache.redis'
        settings['permission_backend'] = 'cliquet.permission.redis'

        settings['project_name'] = 'myapp'
        settings['project_version'] = '0.0.1'
        settings['project_docs'] = 'https://cliquet.rtfd.org/'
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


class FormattedErrorMixin(object):

    def assertFormattedError(self, response, code, errno, error,
                             message=None, info=None):
        # make sure we translate Enum instances to their values
        if isinstance(error, Enum):
            error = error.value

        if isinstance(errno, Enum):
            errno = errno.value

        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=UTF-8')
        self.assertEqual(response.json['code'], code)
        self.assertEqual(response.json['errno'], errno)
        self.assertEqual(response.json['error'], error)

        if message is not None:
            self.assertIn(message, response.json['message'])
        else:
            self.assertNotIn('message', response.json)

        if info is not None:
            self.assertIn(info, response.json['info'])
        else:
            self.assertNotIn('info', response.json)


@implementer(IAuthorizationPolicy)
class AllowAuthorizationPolicy(object):
    def permits(self, context, principals, permission):
        if permission == PRIVATE:
            return Authenticated in principals
        if Everyone in principals:
            return True
        # Cliquet default authz policy uses prefixed_userid.
        prefixed = [context.prefixed_userid]
        return USER_PRINCIPAL in (principals + prefixed)

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
skip_if_no_postgresql = unittest.skipIf(sqlalchemy is None,
                                        "postgresql is not installed.")
