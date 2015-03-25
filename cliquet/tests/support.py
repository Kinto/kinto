import mock
import threading

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest

from cornice import errors as cornice_errors
from pyramid.url import parse_url_overrides

from cliquet import DEFAULT_SETTINGS
from cliquet.utils import random_bytes_hex
from cliquet.tests.testapp import main as testapp


class DummyRequest(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.upath_info = '/v0/'
        self.registry = mock.MagicMock(settings=DEFAULT_SETTINGS)
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors(request=self)
        self.authenticated_userid = 'bob'
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


class FakeAuthentMixin(object):
    def __init__(self, *args, **kwargs):
        super(FakeAuthentMixin, self).__init__(*args, **kwargs)

        self.patcher = mock.patch('cliquet.authentication.'
                                  'OAuthClient.verify_token')
        access_token = 'secret'
        self.headers = {
            'Authorization': 'Bearer {0}'.format(access_token),
        }

    def setUp(self):
        super(FakeAuthentMixin, self).setUp()

        settings = self.app.app.registry.settings

        settings.setdefault('cliquet.userid_hmac_secret',
                            random_bytes_hex(16))

        self.fxa_verify = self.patcher.start()
        self.fxa_verify.return_value = {
            'user': 'bob'
        }

    def tearDown(self):
        super(FakeAuthentMixin, self).tearDown()
        self.patcher.stop()


class BaseWebTest(FakeAuthentMixin):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    api_prefix = "v0"

    def get_test_app(self):
        return webtest.TestApp(testapp(self.get_app_settings()))

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = self.get_test_app()
        self.app.RequestClass = get_request_class(self.api_prefix)
        self.db = self.app.app.registry.storage
        self.headers.update({
            'Content-Type': 'application/json',
        })

    def get_app_settings(self):
        settings = DEFAULT_SETTINGS.copy()
        settings['cliquet.project_name'] = 'cliquet'
        settings['cliquet.project_docs'] = 'https://cliquet.rtfd.org/'
        settings['fxa-oauth.relier.enabled'] = True
        settings['fxa-oauth.oauth_uri'] = 'https://oauth-stable.dev.lcip.org'
        settings['fxa-oauth.webapp.authorized_domains'] = ['*.firefox.com', ]
        return settings

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.db.flush()


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
