import unittest
import mock
import json
import yaml
import tempfile
import os

from kinto.views.swagger import swagger_view
from .support import BaseWebTest


class SwaggerViewTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        try:
            delattr(swagger_view, '__json__')  # Clean-up memoization.
        except AttributeError:
            pass

    tearDown = setUp

    def test_get_spec(self):
        spec_dict = self.app.get('/swagger.json').json
        self.assertIsNotNone(spec_dict)

    def test_404_with_no_files(self):
        with mock.patch('os.path.exists', lambda f: False):
            self.app.get('/swagger.json', status=404)

    def test_extensions_json(self):
        path = tempfile.mktemp(suffix='.json')
        content = {'swagger': '3.0'}
        with open(path, 'w') as f:
            json.dump(content, f)

        self.addCleanup(lambda: os.remove(path))

        with mock.patch.dict(self.app.app.registry.settings, [('includes', 'package')]):
            with mock.patch('pkg_resources.resource_filename', lambda pkg, f: path):
                response = self.app.get('/swagger.json')
                self.assertEquals(response.json['swagger'], '3.0')

    def test_extensions_yaml(self):
        path = tempfile.mktemp(suffix='.yaml')
        content = {'swagger': '3.0'}
        with open(path, 'w') as f:
            yaml.dump(content, f)

        self.addCleanup(lambda: os.remove(path))

        with mock.patch.dict(self.app.app.registry.settings, [('includes', 'package')]):
            with mock.patch('pkg_resources.resource_filename', lambda pkg, f: path):
                response = self.app.get('/swagger.json')
                self.assertEquals(response.json['swagger'], '3.0')
