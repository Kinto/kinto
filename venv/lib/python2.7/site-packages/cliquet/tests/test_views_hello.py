import mock

from .support import BaseWebTest, unittest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['project_version'], "0.0.1")
        self.assertEqual(response.json['cliquet_protocol_version'], "2")
        self.assertEqual(response.json['url'], 'http://localhost/v0/')
        self.assertEqual(response.json['project_name'], 'myapp')
        self.assertEqual(response.json['project_docs'],
                         'https://cliquet.rtfd.org/')

    def test_do_not_returns_eos_if_empty_in_settings(self):
        response = self.app.get('/')
        self.assertNotIn('eos', response.json)

    def test_returns_eos_if_not_empty_in_settings(self):
        eos = '2069-02-21'
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('eos', eos)]):
            response = self.app.get('/')
            self.assertEqual(response.json['eos'], eos)

    def test_public_settings_are_shown_in_view(self):
        response = self.app.get('/')
        settings = response.json['settings']
        expected = {'batch_max_requests': 25, 'readonly': False}
        self.assertEqual(expected, settings)

    def test_public_settings_can_be_set_from_registry(self):
        self.app.app.registry.public_settings.add('myapp.paginate_by')
        response = self.app.get('/')
        settings = response.json['settings']
        self.assertIn('myapp.paginate_by', settings)

    def test_public_settings_can_be_set_with_and_without_prefix(self):
        self.app.app.registry.public_settings.add('myapp.paginate_by')
        self.app.app.registry.public_settings.add('cliquet.paginate_by')
        self.app.app.registry.public_settings.add('project_version')
        response = self.app.get('/')
        settings = response.json['settings']
        self.assertIn('cliquet.paginate_by', settings)
        self.assertIn('myapp.paginate_by', settings)
        self.assertIn('project_version', settings)

    def test_if_user_not_authenticated_no_userid_provided(self):
        response = self.app.get('/')
        self.assertNotIn('user', response.json)

    def test_if_user_authenticated_userid_is_provided(self):
        response = self.app.get('/', headers=self.headers)
        userid = response.json['user']['id']
        self.assertTrue(userid.startswith('basicauth:'),
                        '"%s" does not starts with "basicauth:"' % userid)

    def test_return_http_api_version_when_set(self):
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('http_api_version', '1.2')]):
            response = self.app.get('/')

        self.assertTrue(response.json['http_api_version'])
