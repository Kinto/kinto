import unittest
from . import BaseWebTest


class HelloViewTest(BaseWebTest, unittest.TestCase):

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
