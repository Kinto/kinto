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
        self.w.db.session.query(schemas.ArticleDevice).delete()

    def url_for(self, path):
        return "/v1" + path

    def auth_headers(self, username, password):
        auth_password = base64.b64encode(
            (u'%s:%s' % (username, password)).encode('ascii')) \
            .strip().decode('ascii')
        return {
            'Authorization': 'Basic {0}'.format(auth_password),
        }

    def db_filter(self, schema, **filters):
        _all = self.w.db.session.query(schema)
        return _all.filter_by(**filters)


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
        self.article1 = db.session.merge(self.article1)
        self.assertEqual(len(r.json['_items']), 1)
        self.assertEqual(r.json['_items'][0]['_id'], self.article1.id)

        headers = self.auth_headers(username='john', password='secret')
        r = self.w.get(self.url_for('/articles'), headers=headers)
        self.article2 = db.session.merge(self.article2)
        self.assertEqual(len(r.json['_items']), 1)
        self.assertEqual(r.json['_items'][0]['_id'], self.article2.id)


class ArticleCreation(TestBase, TestCase):
    def test_article_cannot_be_created_anonymously(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        self.w.post(self.url_for('/articles'), record, status=401)

    def test_article_must_have_an_url_and_title(self):
        record = dict(title='')
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.post(self.url_for('/articles'), record, headers=headers, status=422)
        self.assertItemsEqual(['url', 'title'], r.json['_issues'].keys())

    def test_article_urls_must_be_unique(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        headers = self.auth_headers(username='alice', password='secret')
        self.w.post(self.url_for('/articles'), record, headers=headers)
        record['title'] = "Mozilla Corp"
        r = self.w.post(self.url_for('/articles'), record, headers=headers,
                        status=422)
        self.assertIn('url', r.json['_issues'])

    def test_article_is_linked_to_author(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        headers = self.auth_headers(username='john', password='secret')
        r = self.w.post(self.url_for('/articles'), record, headers=headers)
        record_id = r.json['_id']
        record = self.w.db.session.query(schemas.Article).filter_by(id=record_id).first()
        self.assertEqual(record.author, 2)


class DeviceTracking(TestBase, TestCase):
    def setUp(self):
        super(DeviceTracking, self).setUp()
        self.article1 = schemas.Article(title="MoFo",
                                        url="http://mozilla.org",
                                        author=1)
        self.w.db.session.add(self.article1)
        self.w.db.session.commit()
        self.device1 = schemas.ArticleDevice(article=self.article1.id,
                                             device="Manual",
                                             read=50)
        self.w.db.session.add(self.device1)
        self.w.db.session.commit()

    def test_device_is_created_when_article_is_fetched(self):
        headers = self.auth_headers(username='alice', password='secret')
        self.w.get(self.url_for('/articles/%s' % self.article1.id), headers=headers)
        _all = self.db_filter(schemas.ArticleDevice, article=self.article1.id).all()
        self.assertEqual(len(_all), 2)

    def test_useragent_is_used_to_track_device(self):
        headers = self.auth_headers(username='alice', password='secret')
        headers['User-Agent'] = 'WebTest/1.0 (Linux; Ubuntu 14.04)'
        self.w.get(self.url_for('/articles/%s' % self.article1.id), headers=headers)
        device = 'Other-Ubuntu-Other'
        self.assertEqual(len(self.db_filter(schemas.ArticleDevice, device=device).all()), 1)

    def test_can_get_status_of_all_devices(self):
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.get(self.url_for('/articles/%s/devices' % self.article1.id), headers=headers)
        self.assertEqual(len(r.json['_items']), 1)

    def test_can_get_status_by_device(self):
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.get(self.url_for('/articles/%s/devices/Manual' % self.article1.id), headers=headers)
        self.assertEqual(r.json['read'], 50)

    def test_can_patch_read_for_device(self):
        headers = self.auth_headers(username='alice', password='secret')
        r = self.w.get(self.url_for('/articles/%s/devices' % self.article1.id), headers=headers)
        self.assertEqual(len(r.json['_items']), 1)
