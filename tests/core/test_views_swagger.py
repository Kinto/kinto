import os
import unittest
import mock
import tempfile

from ruamel import yaml

from kinto.core.views.swagger import swagger_view
from .support import BaseWebTest


class SwaggerViewTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        try:
            delattr(swagger_view, '__json__')  # Clean-up memoization.
        except AttributeError:
            pass

    tearDown = setUp

    def test_get_spec_at_root(self):
        self.app.get('/__api__')

    def test_404_with_no_files(self):
        with mock.patch('os.path.exists', lambda f: False):
            self.app.get('/__api__', status=404)

    def test_extensions(self):
        path = tempfile.mktemp(suffix='.yaml')
        content = {'swagger': '3.0'}
        with open(path, 'w') as f:
            yaml.dump(content, f)

        self.addCleanup(lambda: os.remove(path))

        with mock.patch.dict(self.app.app.registry.settings, [('includes', 'package')]):
            with mock.patch('pkg_resources.resource_filename', lambda pkg, f: path):
                response = self.app.get('/__api__')
                self.assertEquals(response.json['swagger'], '3.0')

    def test_default_security_extensions(self):
        path = tempfile.mktemp(suffix='.yaml')
        content = {
            'securityDefinitions': {
                'fxa': {
                    'type': 'oauth2',
                    'authorizationUrl': 'https://oauth-stable.dev.lcip.org',
                    'flow': 'implicit',
                    'scopes': {'kinto': 'Basic scope'}
                }
            }
        }
        with open(path, 'w') as f:
            yaml.dump(content, f)

        self.addCleanup(lambda: os.remove(path))

        with mock.patch.dict(self.app.app.registry.settings, [('includes', 'fxa')]):
            with mock.patch('pkg_resources.resource_filename', lambda pkg, f: path):
                response = self.app.get('/__api__')
                self.assertEqual(['basicAuth', 'fxa'],
                                 sorted(response.json['securityDefinitions'].keys()))
                self.assertDictContainsSubset(content['securityDefinitions'],
                                              response.json['securityDefinitions'])
                self.assertIn({'fxa': ['kinto']}, response.json['security'])
