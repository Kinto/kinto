import re

from kinto.tests.support import (BaseWebTest, unittest)


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def get_app_settings(self, extra=None):
        settings = super(HelloViewTest, self).get_app_settings(extra)
        settings['includes'] = 'kinto.plugins.history'
        return settings

    def test_flush_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('history', capabilities)


class HistoryViewTest(BaseWebTest, unittest.TestCase):

    def get_app_settings(self, extra=None):
        settings = super(HistoryViewTest, self).get_app_settings(extra)
        settings['includes'] = 'kinto.plugins.history'
        return settings

    def setUp(self):
        self.app.put('/buckets/test', headers=self.headers)

    def test_only_get_on_collection_is_allowed(self):
        url = '/buckets/test/history'
        self.app.put(url, headers=self.headers, status=405)
        self.app.patch(url, headers=self.headers, status=405)
        self.app.delete(url, headers=self.headers, status=405)

    def test_only_collection_endpoint_is_available(self):
        resp = self.app.get('/buckets/test/history', headers=self.headers)
        entry = resp.json['data'][0]
        url = '/buckets/test/history/%s' % entry['id']
        self.app.get(url, headers=self.headers, status=404)
        self.app.put(url, headers=self.headers, status=404)
        self.app.patch(url, headers=self.headers, status=404)
        self.app.delete(url, headers=self.headers, status=404)

    def test_history_contains_bucket_creation(self):
        resp = self.app.get('/buckets/test/history',
                            headers=self.headers)
        entry = resp.json['data'][0]
        assert entry['resource_name'] == 'bucket'
        assert entry['bucket_id'] == 'test'
        assert entry['action'] == 'create'
        assert entry['userid'].startswith('basicauth:3a0c56')
        assert re.match('^\d{4}\-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}',
                        entry['date'])

    def test_tracks_collection_creation(self):
        resp = self.app.put('/buckets/test/collections/collec',
                            headers=self.headers)
        collection = resp.json['data']
        resp = self.app.get('/buckets/test/history',
                            headers=self.headers)
        entry = resp.json['data'][0]
        assert entry['resource_name'] == 'collection'
        assert entry['bucket_id'] == 'test'
        assert entry['collection_id'] == collection['id']
        assert entry['action'] == 'create'

    def test_tracks_record_creation(self):
        resp = self.app.put('/buckets/test/collections/collec',
                            headers=self.headers)
        collection = resp.json['data']
        resp = self.app.put('/buckets/test/collections/collec/records/rec',
                            headers=self.headers)
        record = resp.json['data']
        resp = self.app.get('/buckets/test/history',
                            headers=self.headers)
        entry = resp.json['data'][0]
        assert entry['resource_name'] == 'record'
        assert entry['bucket_id'] == 'test'
        assert entry['collection_id'] == collection['id']
        assert entry['record_id'] == record['id']
        assert entry['action'] == 'create'
