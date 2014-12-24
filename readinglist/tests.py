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
        self.w.db.session.query(schemas.Device).delete()
        self.w.db.session.query(schemas.ArticleStatus).delete()
        self.patcher.stop()

    def url_for(self, path):
        return "/v1" + path

    def db_filter(self, schema, **filters):
        _all = self.w.db.session.query(schema)
        return _all.filter_by(**filters)


class ArticlesListTest(TestBase, TestCase):
    def setUp(self):
        super(ArticlesListTest, self).setUp()
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


class ArticleCreationTest(TestBase, TestCase):
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


class DeviceListTest(TestBase, TestCase):
    def setUp(self):
        super(DeviceListTest, self).setUp()
        self.device1 = schemas.Device(name="FxOS",
                                      owner="alice")
        self.device2 = schemas.Device(name="Android",
                                      owner="bob")
        self.w.db.session.add(self.device1)
        self.w.db.session.add(self.device2)
        self.w.db.session.commit()

    def test_devices_list_requires_authentication(self):
        self.w.get(self.url_for('/devices'), status=401)

    def test_devices_are_filtered_by_author(self):
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        r = self.w.get(self.url_for('/devices'), headers=self.headers)
        self.device1 = db.session.merge(self.device1)
        self.assertEqual(len(r.json['_items']), 1)
        self.assertEqual(r.json['_items'][0]['_id'], self.device1.id)

        self.fxa_verify.return_value = {
            'user': 'bob'
        }
        r = self.w.get(self.url_for('/devices'), headers=self.headers)
        self.device2 = db.session.merge(self.device2)
        self.assertEqual(len(r.json['_items']), 1)
        self.assertEqual(r.json['_items'][0]['_id'], self.device2.id)


class DeviceCreationTest(TestBase, TestCase):
    def test_device_cannot_be_created_anonymously(self):
        record = dict(name="FxOS")
        self.w.post(self.url_for('/devices'), record, status=401)

    def test_device_must_have_a_name(self):
        record = dict(name='')
        r = self.w.post(self.url_for('/devices'), record,
                        headers=self.headers, status=422)
        self.assertItemsEqual(['name'], r.json['_issues'].keys())

    def test_name_must_be_unique(self):
        record = dict(name="FxOS")
        self.w.post(self.url_for('/devices'), record,
                    headers=self.headers)
        r = self.w.post(self.url_for('/devices'), record,
                        headers=self.headers, status=422)
        self.assertIn('name', r.json['_issues'])

    def test_device_is_linked_to_owner(self):
        self.fxa_verify.return_value = {
            'user': 'silent-bob'
        }
        record = dict(name="FxOS")
        r = self.w.post(self.url_for('/devices'), record,
                        headers=self.headers)
        record_id = r.json['_id']
        record = self.w.db.session.query(schemas.Device)\
                                  .filter_by(id=record_id).first()
        self.assertEqual(record.owner, 'silent-bob')


class ArticleStatusTest(TestBase, TestCase):
    def setUp(self):
        super(ArticleStatusTest, self).setUp()
        self.article = schemas.Article(title="MoFo",
                                        url="http://mozilla.org",
                                        author="alice")
        self.w.db.session.add(self.article)
        self.w.db.session.commit()

        self.device = schemas.Device(name="FxOS")
        self.w.db.session.add(self.device)
        self.w.db.session.commit()

        self.device_status = schemas.ArticleStatus(article=self.article,
                                                   device_id=self.device.id,
                                                   read=50)
        self.w.db.session.add(self.device_status)
        self.w.db.session.commit()

    def test_devices_are_embedded_in_articles(self):
        url = '/articles/%s?embedded={"status": 1}' % self.article.id
        r = self.w.get(self.url_for(url), headers=self.headers)
        self.assertEqual(len(r.json['status']), 1)
        self.assertEqual(r.json['status'][0]['read'], 50)

    def test_can_get_status_of_all_devices(self):
        r = self.w.get(self.url_for('/articles/%s/status' % self.article.id),
                       headers=self.headers)
        self.assertEqual(len(r.json['_items']), 1)

    def test_returns_404_if_device_unknown(self):
        url = '/articles/{0}/status/123'
        self.w.get(self.url_for(url), headers=self.headers, status=404)

    def test_can_post_status_of_device(self):
        record = dict(device_id=self.device.id, read=78)
        url = '/articles/{0}/status'.format(self.article.id)
        r = self.w.post_json(self.url_for(url), record, headers=self.headers)
        record_id = r.json['_id']
        record = self.w.db.session.query(schemas.ArticleStatus)\
                                  .filter_by(id=record_id).first()
        self.assertEqual(record.read, 78)

    def test_fails_to_post_status_of_unknown_device(self):
        record = dict(device_id=314, read=78)
        url = '/articles/{0}/status'.format(self.article.id)
        self.w.post_json(self.url_for(url), record, headers=self.headers,
                         status=422)

    def test_can_get_status_by_device(self):
        url = '/articles/{0}/status/{1}'.format(self.article.id,
                                                self.device.id)
        r = self.w.get(self.url_for(url), headers=self.headers)
        self.assertEqual(r.json['read'], 50)

    def test_can_patch_read_for_device(self):
        device_read = {"read": 75}
        url = '/articles/{0}/status/{1}'.format(self.article.id,
                                                self.device_status.id)
        self.w.patch_json(self.url_for(url), device_read, headers=self.headers)
        self.device_status = self.w.db.session.merge(self.device_status)
        self.assertEqual(self.device_status.read, 75)
