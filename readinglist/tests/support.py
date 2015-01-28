import mock
import threading
import webtest

try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

from readinglist import API_VERSION


class PrefixedRequestClass(webtest.app.TestRequest):

    @classmethod
    def blank(cls, path, *args, **kwargs):
        path = '/%s%s' % (API_VERSION, path)
        return webtest.app.TestRequest.blank(path, *args, **kwargs)


class BaseWebTest(object):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = webtest.TestApp("config:config/readinglist.ini",
                                   relative_to='.')
        self.app.RequestClass = PrefixedRequestClass
        self.db = self.app.app.registry.backend
        self.patcher = mock.patch('readinglist.authentication.'
                                  'OAuthClient.verify_token')
        access_token = 'secret'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(access_token),
        }

    def setUp(self):
        self.fxa_verify = self.patcher.start()
        self.fxa_verify.return_value = {
            'user': 'bob'
        }

    def tearDown(self):
        self.db.flush()
        self.patcher.stop()

    def assertFormattedError(self, response, code, errno, error,
                             message=None, info=None):
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
