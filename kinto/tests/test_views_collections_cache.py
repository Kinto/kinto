from .support import (BaseWebTest, unittest, MINIMALIST_RECORD)


class SettingsExpiresTest(BaseWebTest, unittest.TestCase):
    def get_app_settings(self, extra=None):
        settings = super(SettingsExpiresTest, self).get_app_settings(extra)
        settings['cliquet.record_cache_expires_seconds'] = 3600
        return settings

    def setUp(self):
        super(SettingsExpiresTest, self).setUp()
        r = self.app.post_json('/buckets/default/collections/cached/records',
                               MINIMALIST_RECORD,
                               headers=self.headers)
        self.record = r.json['data']

    def test_expires_and_cache_control_headers_are_set(self):
        url = '/buckets/default/collections/cached/records'
        r = self.app.get(url,
                         headers=self.headers)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')

        r = self.app.get(url + '/%s' % self.record['id'],
                         headers=self.headers)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')


class CollectionExpiresTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(CollectionExpiresTest, self).setUp()
        self.collection_url = '/buckets/default/collections/cached'
        self.app.put_json(self.collection_url,
                          {'data': {'cache_expires': 3600}},
                          headers=self.headers)

        self.records_url = self.collection_url + '/records'

        resp = self.app.post_json(self.records_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self.records_url + '/' + self.record['id']

    def test_cache_expires_must_be_an_integer(self):
        self.app.put_json(self.collection_url,
                          {'data': {'cache_expires': 'abc'}},
                          headers=self.headers,
                          status=400)

    def test_expires_and_cache_control_are_set_on_records(self):
        r = self.app.get(self.records_url,
                         headers=self.headers)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')

    def test_expires_and_cache_control_are_set_on_record(self):
        r = self.app.get(self.record_url,
                         headers=self.headers)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')

    def test_cache_control_is_set_no_cache_if_zero(self):
        self.app.put_json(self.collection_url,
                          {'data': {'cache_expires': 0}},
                          headers=self.headers)
        r = self.app.get(self.records_url,
                         headers=self.headers)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'],
                         'max-age=0, must-revalidate, no-cache, no-store')
        self.assertEqual(r.headers['Pragma'], 'no-cache')

    def test_cache_control_on_collection_overrides_setting(self):
        app = self._get_test_app({'cliquet.record_cache_expires_seconds': 10})
        app.put_json(self.collection_url,
                     {'data': {'cache_expires': 3600}},
                     headers=self.headers)
        r = app.get(self.records_url, headers=self.headers)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')
