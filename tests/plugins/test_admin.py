import unittest
from ..support import BaseWebTest


class AdminViewTest(BaseWebTest, unittest.TestCase):

    def get_app_settings(self, extras=None):
        settings = super(AdminViewTest, self).get_app_settings(extras)
        settings['includes'] = 'kinto.plugins.admin'
        return settings

    def test_capability_is_exposed(self):
        self.maxDiff = None
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('admin', capabilities)
        self.assertIn('version', capabilities['admin'])
        del capabilities['admin']['version']
        expected = {
            "description": "Serves the admin console.",
            "url": ("https://github.com/Kinto/kinto-admin/"),
        }
        self.assertEqual(expected, capabilities['admin'])

    def test_admin_index_cat_be_reached(self):
        self.maxDiff = None
        resp = self.app.get('/admin/')
        assert "html" in resp.body.decode('utf-8')
