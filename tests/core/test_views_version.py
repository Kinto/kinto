import mock
import os
import json
import tempfile
import unittest

from kinto.core.views.version import version_view
from .support import BaseWebTest


class VersionViewTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        try:
            delattr(version_view, '__json__')  # Clean-up memoization.
        except AttributeError:
            pass

    tearDown = setUp

    def test_return_the_version_file_in_current_folder_if_present(self):
        content = {'version': '0.8.1'}
        fake_file = mock.mock_open(read_data=json.dumps(content))
        with mock.patch('os.path.exists'):
            with mock.patch('kinto.core.views.version.open', fake_file, create=True):
                response = self.app.get('/__version__')
                assert response.json == content

    def test_return_a_404_if_version_file_if_not_present(self):
        self.app.get('/__version__', status=404)

    def test_return_the_version_file_specified_in_setting_if_present(self):
        custom_path = tempfile.mktemp()
        content = {'foo': 'lala'}
        with open(custom_path, 'w') as f:
            json.dump(content, f)
        self.addCleanup(lambda: os.remove(custom_path))

        with mock.patch.dict(self.app.app.registry.settings,
                             [('version_json_path', custom_path)]):
            response = self.app.get('/__version__')

        assert response.json == content
