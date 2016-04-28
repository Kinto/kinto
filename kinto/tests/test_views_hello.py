from kinto import __version__ as VERSION

from .support import BaseWebTest, unittest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['project_name'], 'kinto')
        self.assertEqual(response.json['project_version'], VERSION)
        self.assertEqual(response.json['project_docs'],
                         'https://kinto.readthedocs.io/')
        self.assertEqual(response.json['url'], 'http://localhost/v1/')

    def test_hides_user_info_if_anonymous(self):
        response = self.app.get('/')
        self.assertNotIn('user', response.json)

    def test_returns_user_id_if_authenticated(self):
        response = self.app.get('/', headers=self.headers)
        self.assertEqual(response.json['user']['id'],
                         ('basicauth:3a0c56d278def4113f38d0cfff6db1b06b'
                          '84fcc4384ee890cf7bbaa772317e10'))

    def test_capability_is_exposed_if_setting_is_set(self):
        settings = self.get_app_settings()
        settings['experimental_collection_schema_validation'] = True
        app = self._get_test_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('schema', capabilities)
        expected = {
            "description": "Validates collection records with JSON schemas.",
            "url": "http://kinto.readthedocs.io/en/latest/api/1.x/"
                   "collections.html#collection-json-schema",
        }
        self.assertEqual(expected, capabilities['schema'])

    def test_capability_is_exposed_if_setting_is_not_set(self):
        settings = self.get_app_settings()
        settings['experimental_collection_schema_validation'] = False
        app = self._get_test_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertNotIn('schema', capabilities)

    def test_flush_capability_if_enabled(self):
        settings = self.get_app_settings()
        settings['flush_endpoint_enabled'] = True
        app = self._get_test_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('flush_endpoint', capabilities)
        expected = {
            "description": "The __flush__ endpoint can be used to remove "
                           "all data from all backends.",
            "url": "http://kinto.readthedocs.io/en/latest/configuration/"
                   "settings.html#activating-the-flush-endpoint"
        }
        self.assertEqual(expected, capabilities['flush_endpoint'])

    def test_flush_capability_if_not_enabled(self):
        settings = self.get_app_settings()
        settings['flush_endpoint_enabled'] = False
        app = self._get_test_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertNotIn('flush_endpoint', capabilities)
