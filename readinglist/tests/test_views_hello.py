# -*- coding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from webtest.app import TestRequest

from readinglist import __version__ as VERSION, API_VERSION

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

    def test_a_timestamp_header_is_provided_in_responses(self):
        response = self.app.get('/')
        self.assertIsNotNone(response.headers.get('Timestamp'))

    def test_redirect_to_version(self):
        # We don't want the prefix to be automatically added for this test.
        original_request_class = self.app.RequestClass

        try:
            self.app.RequestClass = TestRequest  # Standard RequestClass.

            # GET on the hello view.
            response = self.app.get('/')
            self.assertEqual(response.status_int, 307)
            self.assertEqual(response.location,
                             'http://localhost/%s/' % API_VERSION)

            # GET on the fields view.
            response = self.app.get('/articles')
            self.assertEqual(response.status_int, 307)
            self.assertEqual(response.location,
                             'http://localhost/%s/articles' % API_VERSION)
        finally:
            self.app.RequestClass = original_request_class
