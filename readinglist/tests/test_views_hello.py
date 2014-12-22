import unittest

from readinglist import __version__ as VERSION

from .support import BaseWebTest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['version'], VERSION)
        self.assertEqual(response.json['url'], 'http://localhost')
        self.assertEqual(response.json['readinglist'], 'hello')
