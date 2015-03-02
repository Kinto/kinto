import mock
import threading

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest

from cornice import errors as cornice_errors

from cliquet.utils import random_bytes_hex
from cliquet.tests.testapp import main as testapp


class DummyRequest(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.upath_info = '/v0/'
        self.registry = mock.MagicMock(settings={})
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors(request=self)
        self.authenticated_userid = 'bob'
        self.validated = {}
        self.matchdict = {}
        self.response = mock.MagicMock(headers={})


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

        settings.setdefault('fxa-oauth.oauth_uri', '')
        settings.setdefault('fxa-oauth.scope', '')
        settings.setdefault('cliquet.userid_hmac_secret',
                            random_bytes_hex(16))

        settings.setdefault('cliquet.project_name', 'cliquet')
        settings.setdefault('cliquet.docs', 'https://cliquet.rtfd.org/')

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
        return {
            'cliquet.project_name': 'cliquet',
            'cliquet.project_docs': 'https://cliquet.rtfd.org/',
            'cliquet.storage_backend': 'cliquet.storage.redis',
            'cliquet.session_backend': 'cliquet.session.redis',
            'fxa-oauth.client_id': '89513028159972bc',
            'fxa-oauth.client_secret': '9aced230585cc0aa2932e2eb871c9a3a7d6458'
                                       'e59ccf57eb610ea0a3467dd800',
            'fxa-oauth.oauth_uri': 'https://oauth-stable.dev.lcip.org',
            'fxa-oauth.scope': 'profile'
        }

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
