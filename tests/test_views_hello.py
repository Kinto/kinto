from kinto import __version__ as VERSION

from kinto.core.testing import unittest

from .support import BaseWebTest, MINIMALIST_BUCKET, MINIMALIST_GROUP


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
        self.assertEqual(response.json['user']['id'], self.principal)

    def test_returns_user_principals_if_authenticated(self):
        group_url = '/buckets/beers/groups/users'
        group = {**MINIMALIST_GROUP}
        group['data']['members'].append(self.principal)
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET, headers=self.headers)
        self.app.put_json(group_url, group, headers=self.headers)
        response = self.app.get('/', headers=self.headers).json['user']['principals']
        principals = ('system.Everyone', 'system.Authenticated',
                      group_url, self.principal)
        self.assertEqual(sorted(response), sorted(principals))

    def test_capability_is_exposed_if_setting_is_set(self):
        settings = {'experimental_collection_schema_validation': True}
        app = self.make_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('schema', capabilities)
        expected = {
            "description": "Validates collection records with JSON schemas.",
            "url": "https://kinto.readthedocs.io/en/latest/api/1.x/"
                   "collections.html#collection-json-schema",
        }
        self.assertEqual(expected, capabilities['schema'])

    def test_capability_is_exposed_if_setting_is_not_set(self):
        settings = self.get_app_settings()
        settings['experimental_collection_schema_validation'] = False
        app = self.make_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertNotIn('schema', capabilities)

    def test_permissions_capability_if_enabled(self):
        settings = {'experimental_permissions_endpoint': True}
        app = self.make_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('permissions_endpoint', capabilities)
        expected = {
            "description": "The permissions endpoint can be used to list "
                           "all user objects permissions.",
            "url": "https://kinto.readthedocs.io/en/latest/configuration/"
                   "settings.html#activating-the-permissions-endpoint"
        }
        self.assertEqual(expected, capabilities['permissions_endpoint'])

    def test_permissions_capability_if_not_enabled(self):
        settings = {'experimental_permissions_endpoint': False}
        app = self.make_app(settings=settings)
        resp = app.get('/')
        capabilities = resp.json['capabilities']
        self.assertNotIn('permissions_endpoint', capabilities)
