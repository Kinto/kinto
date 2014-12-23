import unittest

from .support import BaseResourceTest


class ResourceTest(BaseResourceTest, unittest.TestCase):
    resource = 'articlestatus'

    def setUp(self):
        super(ResourceTest, self).setUp()
        self.record['article_id'] = self.article['_id']
        self.collection_url = '/articles/{}/status'.format(self.article['_id'])
        self.item_url = '/articles/{}/status/{}'.format(self.article['_id'],
                                                        self.device['_id'])

    def record_factory(self):
        article = dict(title="MoFo", url="http://mozilla.org")
        self.article = self.db.create('article', u'bob', article)
        device = dict(name="FxOS")
        self.device = self.db.create('device', u'bob', device)

        return dict(device_id=self.device['_id'],
                    read=50)

    def modify_record(self, original):
        return dict(read=75)

    def test_created_status_is_linked_to_article(self):
        body = self.record_factory()
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        record_id = resp.json['_id']
        record = self.db.get(self.resource, u'bob', record_id)
        self.assertIsNotNone(record.get('article_id'))

    def test_post_on_unknown_article(self):
        url = '/articles/unknown/status'
        self.app.post_json(url, {}, headers=self.headers, status=404)

    def test_get_record_unknown(self):
        url = '/articles/unknown/status/{}'.format(self.device['_id'])
        self.app.get(url, headers=self.headers, status=404)
        url = '/articles/{}/status/unknown'.format(self.article['_id'])
        self.app.get(url, headers=self.headers, status=404)

    def test_modify_record_unknown(self):
        url = '/articles/unknown/status/{}'.format(self.device['_id'])
        self.app.patch_json(url, {}, headers=self.headers, status=404)
        url = '/articles/{}/status/unknown'.format(self.article['_id'])
        self.app.patch_json(url, {}, headers=self.headers, status=404)

    def test_delete_record_unknown(self):
        url = '/articles/unknown/status/{}'.format(self.device['_id'])
        self.app.delete(url, {}, headers=self.headers, status=404)
        url = '/articles/{}/status/unknown'.format(self.article['_id'])
        self.app.delete(url, {}, headers=self.headers, status=404)
