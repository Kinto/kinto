from kinto import __version__
from kinto.core.views import version
from .support import BaseWebTest, unittest


class VersionViewTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        self.before = version.VERSION_JSON

    def tearDown(self):
        version.VERSION_JSON = self.before

    def test_returns_info_about_name_version_commit_and_repository(self):
        response = self.app.get('/__version__')
        assert response.json['name'] == "kinto"
        assert response.json['version'] == __version__
        assert response.json['source'] == 'https://github.com/Kinto/kinto'
        assert 'commit' in response.json
        assert len(response.json['commit']) == 40

    def test_return_the_version_file_if_present(self):
        version.VERSION_JSON = {
            "commit": "ce480821debc080d9cf5cb67e9a6ba71b2c3f57e",
            "version": "0.8.1",
            "name": "kinto-dist",
            "source": "https://github.com/mozilla-services/kinto-dist"
        }
        response = self.app.get('/__version__')

        assert response.json == version.VERSION_JSON
