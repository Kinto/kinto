try:
    import unittest2 as unittest
except ImportError:
    import unittest

from readinglist import __version__ as VERSION

from .support import BaseWebTest


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_info_about_url_and_version(self):
        response = self.app.get('/')
        self.assertEqual(response.json['version'], VERSION)
        self.assertEqual(response.json['url'], 'http://localhost')
        self.assertEqual(response.json['hello'], 'readinglist')

    def test_returns_none_if_eos_empty_in_settings(self):
        response = self.app.get('/')
        self.assertEqual(response.json['eos'], None)
