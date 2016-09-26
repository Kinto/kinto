import mock
import os
import json
import tempfile
import unittest

from kinto.core.views.version import version_view
from .support import BaseWebTest


class VersionViewTest(BaseWebTest, unittest.TestCase):
    def tearDown(self):
        try:
            os.remove('version.json')  # Clean-up file at default location.
        except OSError:
            pass
        try:
            delattr(version_view, '__json__')  # Clean-up memoization.
        except AttributeError:
            pass

    def test_return_the_version_file_in_current_folder_if_present(self):
        with open('version.json', 'w') as f:
            json.dump({'version': '0.8.1'}, f)

        response = self.app.get('/__version__')
        assert 'version' in response.json

    def test_return_a_404_if_version_file_if_not_present(self):
        self.app.get('/__version__', status=404)

    def test_return_the_version_file_specified_in_setting_if_present(self):
        custom_path = tempfile.mktemp()
        with open(custom_path, 'w') as f:
            json.dump({'foo': 'lala'}, f)
        self.addCleanup(lambda: os.remove(custom_path))

        with mock.patch.dict(self.app.app.registry.settings,
                             [('version_json_path', custom_path)]):
            response = self.app.get('/__version__')

        assert 'foo' in response.json
