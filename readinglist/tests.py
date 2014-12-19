import mock
from unittest import TestCase
from flask.ext.webtest import TestApp
from readinglist.run import app, db
from readinglist import schemas


class TestBase(object):
    def setUp(self):
        self.app = app
        self.w = TestApp(self.app, db=db, use_session_scopes=True)

        self.patcher = mock.patch('readinglist.fxa.verify_token')
        self.fxa_verify = self.patcher.start()
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        self.headers = {
            'Authorization': 'Bearer foo'
        }

    def tearDown(self):
        self.w.db.session.query(schemas.Article).delete()
        self.w.db.session.query(schemas.ArticleDevice).delete()
        self.patcher.stop()

    def url_for(self, path):
        return "/v1" + path

    def db_filter(self, schema, **filters):
        _all = self.w.db.session.query(schema)
        return _all.filter_by(**filters)


class ArticlesList(TestBase, TestCase):
    def setUp(self):
        super(ArticlesList, self).setUp()
        self.article1 = schemas.Article(title="MoFo",
                                        url="http://mozilla.org",
                                        author="alice")
        self.article2 = schemas.Article(title="MoCo",
                                        url="http://mozilla.com",
                                        author="bob")
        self.w.db.session.add(self.article1)
        self.w.db.session.add(self.article2)
        self.w.db.session.commit()

    def test_articles_list_requires_authentication(self):
        self.w.get(self.url_for('/articles'), status=401)

    def test_articles_are_filtered_by_author(self):
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        r = self.w.get(self.url_for('/articles'), headers=self.headers)
        self.article1 = db.session.merge(self.article1)
        self.assertEqual(len(r.json['_items']), 1)
        self.assertEqual(r.json['_items'][0]['_id'], self.article1.id)

        self.fxa_verify.return_value = {
            'user': 'bob'
        }
        r = self.w.get(self.url_for('/articles'), headers=self.headers)
        self.article2 = db.session.merge(self.article2)
        self.assertEqual(len(r.json['_items']), 1)
        self.assertEqual(r.json['_items'][0]['_id'], self.article2.id)


class ArticleCreation(TestBase, TestCase):
    def test_article_cannot_be_created_anonymously(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        self.w.post(self.url_for('/articles'), record, status=401)

    def test_article_must_have_an_url_and_title(self):
        record = dict(title='')
        r = self.w.post(self.url_for('/articles'), record,
                        headers=self.headers, status=422)
        self.assertItemsEqual(['url', 'title'], r.json['_issues'].keys())

    def test_article_urls_must_be_unique(self):
        record = dict(title="MoCo", url="http://mozilla.com")
        self.w.post(self.url_for('/articles'), record,
                    headers=self.headers)
        record['title'] = "Mozilla Corp"
        r = self.w.post(self.url_for('/articles'), record,
                        headers=self.headers, status=422)
        self.assertIn('url', r.json['_issues'])

    def test_article_is_linked_to_author(self):
        self.fxa_verify.return_value = {
            'user': 'silent-bob'
        }
        record = dict(title="MoCo", url="http://mozilla.com")
        r = self.w.post(self.url_for('/articles'), record,
                        headers=self.headers)
        record_id = r.json['_id']
        record = self.w.db.session.query(schemas.Article)\
                                  .filter_by(id=record_id).first()
        self.assertEqual(record.author, 'silent-bob')


class DeviceTracking(TestBase, TestCase):
    def setUp(self):
        super(DeviceTracking, self).setUp()
        self.article1 = schemas.Article(title="MoFo",
                                        url="http://mozilla.org",
                                        author="alice")
        self.w.db.session.add(self.article1)
        self.w.db.session.commit()
        self.device1 = schemas.ArticleDevice(article=self.article1,
                                             device="Manual",
                                             read=50)
        self.w.db.session.add(self.device1)
        self.w.db.session.commit()

    def test_devices_are_embedded_in_articles(self):
        url = '/articles/%s?embedded={"devices": 1}' % self.article1.id
        r = self.w.get(self.url_for(url), headers=self.headers)
        self.assertEqual(len(r.json['devices']), 2)
        self.assertEqual(r.json['devices'][0]['read'], 50)

    def test_device_is_created_when_article_is_fetched(self):
        self.w.get(self.url_for('/articles/%s' % self.article1.id),
                   headers=self.headers)
        queryset = self.db_filter(schemas.ArticleDevice, article=self.article1)
        self.assertEqual(len(queryset.all()), 2)

    def test_device_is_not_recreated_if_it_exists(self):
        for i in range(2):
            self.w.get(self.url_for('/articles/%s' % self.article1.id),
                       headers=self.headers)
        queryset = self.db_filter(schemas.ArticleDevice, article=self.article1)
        self.assertEqual(len(queryset.all()), 2)

    def test_useragent_is_used_to_track_device(self):
        headers = self.headers.copy()
        headers['User-Agent'] = 'WebTest/1.0 (Linux; Ubuntu 14.04)'
        url = '/articles/%s' % self.article1.id
        self.w.get(self.url_for(url), headers=headers)
        device = 'Other-Ubuntu-Other'
        queryset = self.db_filter(schemas.ArticleDevice, device=device)
        self.assertEqual(len(queryset.all()), 1)

    def test_can_get_status_of_all_devices(self):
        r = self.w.get(self.url_for('/articles/%s/devices' % self.article1.id),
                       headers=self.headers)
        self.assertEqual(len(r.json['_items']), 1)

    def test_can_get_status_by_device(self):
        url = '/articles/%s/devices/Manual' % self.article1.id
        r = self.w.get(self.url_for(url), headers=self.headers)
        self.assertEqual(r.json['read'], 50)

    def test_can_patch_read_for_device(self):
        device_read = {"read": 75}
        url = '/articles/%s/devices/%s' % (self.article1.id, self.device1.id)
        self.w.patch_json(self.url_for(url), device_read, headers=self.headers)
        self.device1 = self.w.db.session.merge(self.device1)
        self.assertEqual(self.device1.read, 75)
