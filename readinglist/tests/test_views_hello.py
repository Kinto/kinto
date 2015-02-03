import mock
from webtest.app import TestRequest

from readinglist import __version__ as VERSION, API_VERSION

from .support import BaseWebTest, unittest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['version'], VERSION)
        self.assertEqual(response.json['url'], 'http://localhost')
        self.assertEqual(response.json['hello'], 'readinglist')
        self.assertEqual(response.json['documentation'],
                         'https://readinglist.rtfd.org/')

    def test_do_not_returns_eos_if_empty_in_settings(self):
        response = self.app.get('/')
        self.assertNotIn('eos', response.json)

    def test_returns_eos_if_not_empty_in_settings(self):
        eos = '2069-02-21'
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('readinglist.eos', eos)]):
            response = self.app.get('/')
            self.assertEqual(response.json['eos'], eos)

    def test_redirect_to_version(self):
        # We don't want the prefix to be automatically added for this test.
        original_request_class = self.app.RequestClass

        try:
            self.app.RequestClass = TestRequest  # Standard RequestClass.

            # GET on the hello view.
            response = self.app.get('/')
            self.assertEqual(response.status_int, 307)
            self.assertEqual(response.location,
                             'http://localhost/%s/' % API_VERSION)

            # GET on the fields view.
            response = self.app.get('/articles')
            self.assertEqual(response.status_int, 307)
            self.assertEqual(response.location,
                             'http://localhost/%s/articles' % API_VERSION)
        finally:
            self.app.RequestClass = original_request_class
