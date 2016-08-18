from kinto.core.views import version
from .support import BaseWebTest, unittest


class VersionViewTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        self.VERSION_JSON_before = version.VERSION_JSON
        self.ORIGIN_before = version.ORIGIN

    def tearDown(self):
        version.VERSION_JSON = self.VERSION_JSON_before
        version.ORIGIN = self.ORIGIN_before

    def test_return_the_version_file_if_present(self):
        version.VERSION_JSON = {
            "commit": "ce480821debc080d9cf5cb67e9a6ba71b2c3f57e",
            "version": "0.8.1",
            "name": "kinto-dist",
            "source": "https://github.com/mozilla-services/kinto-dist"
        }
        response = self.app.get('/__version__')

        assert response.json == version.VERSION_JSON

    def test_return_a_404_if_version_file_if_not_present(self):
        version.VERSION_JSON = None
        self.app.get('/__version__', status=404)
