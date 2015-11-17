from .support import (BaseWebTest, unittest, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class GlobalSettingsTest(BaseWebTest, unittest.TestCase):
    def get_app_settings(self, extra=None):
        settings = super(GlobalSettingsTest, self).get_app_settings(extra)
        settings['kinto.record_cache_expires_seconds'] = 3600
        settings['kinto.record_read_principals'] = 'system.Everyone'
        return settings

    def setUp(self):
        super(GlobalSettingsTest, self).setUp()
        self.create_bucket('blog')
        self.app.put_json('/buckets/blog/collections/cached',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        r = self.app.post_json('/buckets/blog/collections/cached/records',
                               MINIMALIST_RECORD,
                               headers=self.headers)
        self.record = r.json['data']

    def test_expires_and_cache_control_headers_are_set(self):
        url = '/buckets/blog/collections/cached/records'
        r = self.app.get(url)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')

        r = self.app.get(url + '/%s' % self.record['id'])
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')


class SpecificSettingsTest(BaseWebTest, unittest.TestCase):
    def get_app_settings(self, extra=None):
        settings = super(SpecificSettingsTest, self).get_app_settings(extra)
        settings['kinto.blog_record_cache_expires_seconds'] = 30
        settings['kinto.browser_top500_record_cache_expires_seconds'] = 60
        return settings

    def setUp(self):
        super(SpecificSettingsTest, self).setUp()

        def create_record_in_collection(bucket_id, collection_id):
            bucket = MINIMALIST_BUCKET.copy()
            bucket['permissions'] = {'read': ['system.Everyone']}
            self.app.put_json('/buckets/%s' % bucket_id,
                              bucket,
                              headers=self.headers)
            collection_url = '/buckets/%s/collections/%s' % (bucket_id,
                                                             collection_id)
            self.app.put_json(collection_url,
                              MINIMALIST_COLLECTION,
                              headers=self.headers)
            r = self.app.post_json(collection_url + '/records',
                                   MINIMALIST_RECORD,
                                   headers=self.headers)
            return r.json['data']

        self.blog_record = create_record_in_collection('blog', 'cached')
        self.app_record = create_record_in_collection('browser', 'top500')

    def assertHasCache(self, url, age):
        r = self.app.get(url)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=%s' % age)

    def test_for_records_on_a_specific_bucket(self):
        collection_url = '/buckets/blog/collections/cached/records'
        self.assertHasCache(collection_url, 30)
        record_url = collection_url + '/%s' % self.blog_record['id']
        self.assertHasCache(record_url, 30)

    def test_for_records_on_a_specific_collection(self):
        collection_url = '/buckets/browser/collections/top500/records'
        self.assertHasCache(collection_url, 60)
        record_url = collection_url + '/%s' % self.app_record['id']
        self.assertHasCache(record_url, 60)


class CollectionExpiresTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(CollectionExpiresTest, self).setUp()
        bucket = MINIMALIST_BUCKET.copy()
        bucket['permissions'] = {'read': ['system.Everyone']}
        self.app.put_json('/buckets/blog',
                          bucket,
                          headers=self.headers)
        self.collection_url = '/buckets/blog/collections/cached'
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

    def test_expires_and_cache_control_are_not_set_if_authenticated(self):
        r = self.app.get(self.records_url, headers=self.headers)
        self.assertNotIn('Expires', r.headers)
        self.assertIn('Cache-Control', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'no-cache')

    def test_expires_and_cache_control_are_set_on_records(self):
        r = self.app.get(self.records_url)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')

    def test_expires_and_cache_control_are_set_on_record(self):
        r = self.app.get(self.record_url)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')

    def test_cache_control_is_set_no_cache_if_zero(self):
        self.app.put_json(self.collection_url,
                          {'data': {'cache_expires': 0}},
                          headers=self.headers)
        r = self.app.get(self.records_url)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'],
                         'max-age=0, must-revalidate, no-cache, no-store')
        self.assertEqual(r.headers['Pragma'], 'no-cache')

    def test_cache_control_on_collection_overrides_setting(self):
        app = self._get_test_app({
            'kinto.record_cache_expires_seconds': 10,
            'kinto.record_read_principals': 'system.Everyone'
        })
        app.put_json('/buckets/blog', MINIMALIST_BUCKET, headers=self.headers)
        app.put_json(self.collection_url,
                     {'data': {'cache_expires': 3600}},
                     headers=self.headers)
        r = app.get(self.records_url)
        self.assertIn('Expires', r.headers)
        self.assertEqual(r.headers['Cache-Control'], 'max-age=3600')
