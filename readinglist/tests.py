from unittest import TestCase
from flask.ext.webtest import TestApp
from readinglist import app, db


class TestBase(object):
    def setUp(self):
        self.app = app
        self.w = TestApp(self.app, db=db, use_session_scopes=True)


class HomeTest(TestBase, TestCase):
    def test_root_url_redirects_to_prefix(self):
        r = self.w.get('/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], 'http://localhost:80/v1')