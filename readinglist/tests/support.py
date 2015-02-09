import mock
import threading

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import webtest
from cornice import errors as cornice_errors

from readinglist import API_VERSION
from readinglist.utils import random_bytes_hex


class DummyRequest(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.registry = mock.MagicMock(settings={})
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors()
        self.authenticated_userid = 'bob'
        self.validated = {}
        self.matchdict = {}
        self.response = mock.MagicMock(headers={})


class PrefixedRequestClass(webtest.app.TestRequest):

    @classmethod
    def blank(cls, path, *args, **kwargs):
        path = '/%s%s' % (API_VERSION, path)
        return webtest.app.TestRequest.blank(path, *args, **kwargs)


class FakeAuthentMixin(object):
    def __init__(self, *args, **kwargs):
        super(FakeAuthentMixin, self).__init__(*args, **kwargs)

        self.patcher = mock.patch('readinglist.authentication.'
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
        settings.setdefault('readinglist.userid_hmac_secret',
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

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = webtest.TestApp("config:config/readinglist.ini",
                                   relative_to='.')
        self.app.RequestClass = PrefixedRequestClass
        self.db = self.app.app.registry.storage
        self.headers.update({
            'Content-Type': 'application/json',
        })

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
