import mock

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
