import base64

from unittest import TestCase
from flask.ext.webtest import TestApp
from readinglist.run import app, db
from readinglist import schemas


class TestBase(object):
    def setUp(self):
        self.app = app
        self.w = TestApp(self.app, db=db, use_session_scopes=True)

    def tearDown(self):
        self.w.db.session.query(schemas.Article).delete()

    def url_for(self, path):
        return "/v1" + path

    def auth_headers(self, username, password):
        auth_password = base64.b64encode(
            (u'%s:%s' % (username, password)).encode('ascii')) \
            .strip().decode('ascii')
        return {
            'Authorization': 'Basic {0}'.format(auth_password),
        }


class HomeTest(TestBase, TestCase):
    def test_root_url_redirects_to_prefix(self):
        r = self.w.get('/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], 'http://localhost:80/v1')

    def test_docs_are_available_with_prefix(self):
        self.w.get('/v1/docs/')


class ArticlesList(TestBase, TestCase):
    def setUp(self):
        super(ArticlesList, self).setUp()
        self.article1 = schemas.Article(title="MoFo",
                                        url="http://mozilla.org",
                                        author=1)
        self.article2 = schemas.Article(title="MoCo",
                                        url="http://mozilla.com",
                                        author=2)
        self.w.db.session.add(self.article1)
        self.w.db.session.add(self.article2)
        self.w.db.session.commit()

    def test_articles_list_requires_authentication(self):
        self.w.get(self.url_for('/articles'), status=401)

    def test_articles_are_filtered_by_author(self):
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.get(self.url_for('/articles'), headers=headers)
        self.assertEqual(len(r.json['_items']), 1)

        headers = self.auth_headers(username='john', password='secret')
        r = self.w.get(self.url_for('/articles'), headers=headers)
        self.assertEqual(len(r.json['_items']), 1)


class ArticleCreation(TestBase, TestCase):
    def test_article_cannot_be_created_anonymously(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        self.w.post(self.url_for('/articles'), record, status=401)

    def test_article_must_have_an_url_and_title(self):
        record = dict(status='read')
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.post(self.url_for('/articles'), record, headers=headers, status=422)
        self.assertItemsEqual(['url', 'title'], r.json['_issues'])

    def test_article_is_linked_to_author(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.post(self.url_for('/articles'), record, headers=headers)
        record_id = r.json['_id']
        record = self.w.db.session.query(schemas.Article).filter_by(id=record_id).first()
        self.assertEqual(record.author, 1)
