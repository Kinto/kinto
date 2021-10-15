import os
import threading
import unittest
from collections import defaultdict
from unittest import mock

import webtest
from cornice import errors as cornice_errors
from pyramid.url import parse_url_overrides

from kinto.core import DEFAULT_SETTINGS, statsd
from kinto.core.storage import generators
from kinto.core.utils import encode64, follow_subrequest, memcache, sqlalchemy

skip_if_ci = unittest.skipIf("CI" in os.environ, "ci")
skip_if_no_postgresql = unittest.skipIf(sqlalchemy is None, "postgresql is not installed.")
skip_if_no_memcached = unittest.skipIf(memcache is None, "memcached is not installed.")
skip_if_no_statsd = unittest.skipIf(not statsd.statsd_module, "statsd is not installed.")


class DummyRequest(mock.MagicMock):
    """Fully mocked request."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.upath_info = "/v0/"
        self.registry = mock.MagicMock(settings={**DEFAULT_SETTINGS})
        self.registry.id_generators = defaultdict(generators.UUID4)
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors()
        self.authenticated_userid = "bob"
        self.authn_type = "basicauth"
        self.prefixed_userid = "basicauth:bob"
        self.effective_principals = ["system.Everyone", "system.Authenticated", "bob"]
        self.prefixed_principals = self.effective_principals + [self.prefixed_userid]
        self.json = {}
        self.validated = {}
        self.log_context = lambda **kw: kw
        self.matchdict = {}
        self.response = mock.MagicMock(headers={})
        self.application_url = ""  # used by parse_url_overrides

        def route_url(*a, **kw):
            # XXX: refactor DummyRequest to take advantage of `pyramid.testing`
            parts = parse_url_overrides(self, kw)
            return "".join([p for p in parts if p])

        self.route_url = route_url

    follow_subrequest = follow_subrequest


def get_request_class(prefix):
    class PrefixedRequestClass(webtest.app.TestRequest):
        @classmethod
        def blank(cls, path, *args, **kwargs):
            if prefix:
                path = f"/{prefix}{path}"
            return webtest.app.TestRequest.blank(path, *args, **kwargs)

    return PrefixedRequestClass


class FormattedErrorMixin:
    """Test mixin in order to perform advanced error responses assertions."""

    def assertFormattedError(self, response, code, errno, error, message=None, info=None):
        self.assertIn("application/json", response.headers["Content-Type"])
        self.assertEqual(response.json["code"], code)
        self.assertEqual(response.json["errno"], errno.value)
        self.assertEqual(response.json["error"], error)
        if message is not None:
            self.assertIn(message, response.json["message"])
        else:  # pragma: no cover
            self.assertNotIn("message", response.json)

        if info is not None:
            self.assertIn(info, response.json["info"])
        else:  # pragma: no cover
            self.assertNotIn("info", response.json)


def get_user_headers(user, password="secret"):
    """Helper to obtain a Basic Auth authorization headers from the specified
    `user` (e.g. ``"user:pass"``)

    :rtype: dict
    """
    credentials = f"{user}:{password}"
    authorization = f"Basic {encode64(credentials)}"
    return {"Authorization": authorization}


class BaseWebTest:
    """Base Web Test to test your kinto.core service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"
    """URL version prefix"""

    entry_point = None
    """Main application entry"""

    headers = {"Content-Type": "application/json"}

    @classmethod
    def setUpClass(cls):
        cls.app = cls.make_app()
        cls.storage = cls.app.app.registry.storage
        cls.cache = cls.app.app.registry.cache
        cls.permission = cls.app.app.registry.permission

        cls.storage.initialize_schema()
        cls.permission.initialize_schema()
        cls.cache.initialize_schema()

    @classmethod
    def make_app(cls, settings=None, config=None):
        """Instantiate the application and setup requests to use the api
        prefix.

        :param dict settings: extra settings values
        :param pyramid.config.Configurator config: already initialized config
        :returns: webtest application instance
        """
        settings = cls.get_app_settings(extras=settings)

        main = cls.entry_point

        wsgi_app = main({}, config=config, **settings)
        app = webtest.TestApp(wsgi_app)
        app.RequestClass = get_request_class(cls.api_prefix)
        return app

    @classmethod
    def get_app_settings(cls, extras=None):
        """Application settings to be used. Override to tweak default settings
        for the tests.

        :param dict extras: extra settings values
        :rtype: dict
        """
        settings = {**DEFAULT_SETTINGS}

        settings["storage_backend"] = "kinto.core.storage.memory"
        settings["cache_backend"] = "kinto.core.cache.memory"
        settings["permission_backend"] = "kinto.core.permission.memory"

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
