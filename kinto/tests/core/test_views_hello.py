import mock
from pyramid import testing

from .support import BaseWebTest, unittest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['project_version'], "0.0.1")
        self.assertEqual(response.json['url'], 'http://localhost/v0/')
        self.assertEqual(response.json['project_name'], 'myapp')
        self.assertEqual(response.json['project_docs'],
                         'https://kinto.rtfd.org/')

    def test_does_not_escape_forward_slashes(self):
        response = self.app.get('/')
        self.assertNotIn('\\/', str(response.body))

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
        self.app.app.registry.public_settings.add('paginate_by')
        response = self.app.get('/')
        settings = response.json['settings']
        self.assertIn('paginate_by', settings)

    def test_if_user_not_authenticated_no_userid_provided(self):
        response = self.app.get('/')
        self.assertNotIn('user', response.json)

    def test_if_user_authenticated_userid_is_provided(self):
        response = self.app.get('/', headers=self.headers)
        userid = response.json['user']['id']
        self.assertTrue(userid.startswith('basicauth:'),
                        '"%s" does not start with "basicauth:"' % userid)

    def test_vary_header_is_present(self):
        response = self.app.get('/', headers=self.headers)
        self.assertIn('Vary', response.headers)
        self.assertIn('Authorization', response.headers['Vary'])

    def test_return_http_api_version_when_set(self):
        with mock.patch.dict(
                self.app.app.registry.settings,
                [('http_api_version', '1.2')]):
            response = self.app.get('/')

        self.assertTrue(response.json['http_api_version'])


class APICapabilitiesTest(BaseWebTest, unittest.TestCase):
    def test_list_of_capabilities_is_empty_by_default(self):
        app = self.make_app()
        response = app.get('/')
        capabilities = response.json['capabilities']
        self.assertEqual(capabilities, {})

    def test_capabilities_can_be_specified_via_config(self):
        config = testing.setUp(settings=self.get_app_settings())
        app = self.make_app(config=config)

        config.add_api_capability("cook-coffee")

        response = app.get('/')
        capabilities = response.json['capabilities']
        expected = {"cook-coffee": {"description": "", "url": ""}}
        self.assertEqual(capabilities, expected)

    def test_capabilities_can_have_arbitrary_attributes(self):
        config = testing.setUp(settings=self.get_app_settings())
        app = self.make_app(config=config)

        capability = dict(description="Track record change",
                          url="https://github.com/Kinto/kinto-changes",
                          status="beta")
        config.add_api_capability("record-changes", **capability)

        response = app.get('/')
        capabilities = response.json['capabilities']
        self.assertEqual(capabilities["record-changes"], capability)

    def test_capability_fails_if_already_registered(self):
        config = testing.setUp(settings=self.get_app_settings())
        self.make_app(config=config)

        config.add_api_capability("cook-coffee")
        with self.assertRaises(ValueError):
            config.add_api_capability("cook-coffee")
