import os
import threading
import unittest
from collections import defaultdict

import mock
import webtest
from cornice import errors as cornice_errors
from pyramid.url import parse_url_overrides

from kinto.core import DEFAULT_SETTINGS
from kinto.core import statsd
from kinto.core.storage import generators
from kinto.core.utils import sqlalchemy, follow_subrequest, encode64

skip_if_travis = unittest.skipIf('TRAVIS' in os.environ, "travis")
skip_if_no_postgresql = unittest.skipIf(sqlalchemy is None, "postgresql is not installed.")
skip_if_no_statsd = unittest.skipIf(not statsd.statsd_module, "statsd is not installed.")


class DummyRequest(mock.MagicMock):
    """Fully mocked request.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.upath_info = '/v0/'
        self.registry = mock.MagicMock(settings={**DEFAULT_SETTINGS})
        self.registry.id_generators = defaultdict(generators.UUID4)
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors()
        self.authenticated_userid = 'bob'
        self.authn_type = 'basicauth'
        self.prefixed_userid = 'basicauth:bob'
        self.effective_principals = [
            'system.Everyone',
            'system.Authenticated',
            'bob']
        self.prefixed_principals = self.effective_principals + [self.prefixed_userid]
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
                path = '/{prefix}{path}'.format(prefix=prefix, path=path)
            return webtest.app.TestRequest.blank(path, *args, **kwargs)

    return PrefixedRequestClass


class FormattedErrorMixin:
    """Test mixin in order to perform advanced error responses assertions.
    """

    def assertFormattedError(self, response, code, errno, error,
                             message=None, info=None):
        self.assertIn('application/json', response.headers['Content-Type'])
        self.assertEqual(response.json['code'], code)
        self.assertEqual(response.json['errno'], errno.value)
        self.assertEqual(response.json['error'], error)
        if message is not None:
            self.assertIn(message, response.json['message'])
        else:  # pragma: no cover
            self.assertNotIn('message', response.json)

        if info is not None:
            self.assertIn(info, response.json['info'])
        else:  # pragma: no cover
            self.assertNotIn('info', response.json)


def get_user_headers(user):
    """Helper to obtain a Basic Auth authorization headers from the specified
    `user` (e.g. ``"user:pass"``)

    :rtype: dict
    """
    credentials = "{}:secret".format(user)
    authorization = 'Basic {}'.format(encode64(credentials))
    return {
        'Authorization': authorization
    }


class BaseWebTest:
    """Base Web Test to test your kinto.core service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"
    """URL version prefix"""

    entry_point = None
    """Main application entry"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = self.make_app()
        self.storage = self.app.app.registry.storage
        self.cache = self.app.app.registry.cache
        self.permission = self.app.app.registry.permission

        self.storage.initialize_schema()
        self.permission.initialize_schema()
        self.cache.initialize_schema()

        self.headers = {
            'Content-Type': 'application/json'
        }

    def make_app(self, settings=None, config=None):
        """Instantiate the application and setup requests to use the api
        prefix.

        :param dict settings: extra settings values
        :param pyramid.config.Configurator config: already initialized config
        :returns: webtest application instance
        """
        settings = self.get_app_settings(extras=settings)

        try:
            main = self.entry_point.__func__
        except AttributeError:  # pragma: no cover
            main = self.entry_point.im_func

        wsgi_app = main({}, config=config, **settings)
        app = webtest.TestApp(wsgi_app)
        app.RequestClass = get_request_class(self.api_prefix)
        return app

    def get_app_settings(self, extras=None):
        """Application settings to be used. Override to tweak default settings
        for the tests.

        :param dict extras: extra settings values
        :rtype: dict
        """
        settings = {**DEFAULT_SETTINGS}

        settings['storage_backend'] = 'kinto.core.storage.memory'
        settings['cache_backend'] = 'kinto.core.cache.memory'
        settings['permission_backend'] = 'kinto.core.permission.memory'

        settings.update(extras or None)

        return settings

    def tearDown(self):
        super().tearDown()
        self.storage.flush()
        self.cache.flush()
        self.permission.flush()


class ThreadMixin:

    def setUp(self):
        super().setUp()
        self._threads = []

    def tearDown(self):
        super().tearDown()

        for thread in self._threads:
            thread.join()

    def _create_thread(self, *args, **kwargs):
        thread = threading.Thread(*args, **kwargs)
        self._threads.append(thread)
        return thread
