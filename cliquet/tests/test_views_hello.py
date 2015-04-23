import mock
from webtest.app import TestRequest

from .support import BaseWebTest, unittest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['version'], "0.0.1")
        self.assertEqual(response.json['url'], 'http://localhost/v0/')
        self.assertEqual(response.json['hello'], 'cliquet')
        self.assertEqual(response.json['documentation'],
                         'https://cliquet.rtfd.org/')

    def test_do_not_returns_eos_if_empty_in_settings(self):
        response = self.app.get('/')
        self.assertNotIn('eos', response.json)

    def test_returns_eos_if_not_empty_in_settings(self):
        eos = '2069-02-21'
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('cliquet.eos', eos)]):
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
                             'http://localhost/v0/')

            # GET on the fields view.
            response = self.app.get('/mushrooms')
            self.assertEqual(response.status_int, 307)
            self.assertEqual(response.location,
                             'http://localhost/v0/mushrooms')
        finally:
            self.app.RequestClass = original_request_class

    def test_do_not_redirect_to_version_if_disabled_in_settings(self):
        # GET on the hello view.
        app = self._get_test_app({
            'cliquet.version_prefix_redirect_enabled': False
        })
        response = app.get('/')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.location, None)
