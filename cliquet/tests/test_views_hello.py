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

    def test_public_settings_are_shown_in_view(self):
        response = self.app.get('/')
        settings = response.json['settings']
        expected = {'cliquet.batch_max_requests': 25}
        self.assertEqual(expected, settings)

    def test_public_settings_can_be_set_from_registry(self):
        self.app.app.registry.public_settings.add('cliquet.paginate_by')
        response = self.app.get('/')
        settings = response.json['settings']
        self.assertIn('cliquet.paginate_by', settings)
