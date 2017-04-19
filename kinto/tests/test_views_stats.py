from pyramid.security import Authenticated

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET)

EMPTY_RECORD_SIZE = 75


class BucketStatsViewTest(BaseWebTest, unittest.TestCase):

    bucket_url = '/buckets/beers'
    bucket_stats_url = '/buckets/beers/stats'

    def setUp(self):
        super(BucketStatsViewTest, self).setUp()
        self.app.put_json(self.bucket_url,
                          MINIMALIST_BUCKET,
                          headers=self.headers)

    def test_empty_buckets_have_empty_stats(self):
        resp = self.app.get(self.bucket_stats_url, headers=self.headers)
        assert resp.json == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": 0,
        }

    def test_buckets_stats_access_is_protected(self):
        self.app.get(self.bucket_stats_url,
                     headers=get_user_headers('alice'),
                     status=403)

    def test_buckets_stats_access_needs_read_access(self):
        self.app.patch_json(self.bucket_url,
                            {'permissions': {'read': [Authenticated]}},
                            headers=self.headers)
        self.app.get(self.bucket_stats_url,
                     headers=get_user_headers('alice'))

    def test_buckets_stats_count_collections(self):
        self.app.post(self.bucket_url + '/collections',
                      headers=self.headers)
        self.app.post(self.bucket_url + '/collections',
                      headers=self.headers)
        self.app.post(self.bucket_url + '/collections',
                      headers=self.headers)
        resp = self.app.get(self.bucket_stats_url, headers=self.headers)
        assert resp.json == {
            "collection_count": 3,
            "record_count": 0,
            "storage_size": 0,
        }

    def test_buckets_stats_ignore_deleted_collections(self):
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id = resp.json['data']['id']
        self.app.delete('%s/collections/%s' % (self.bucket_url, collection_id),
                        headers=self.headers)
        resp = self.app.get(self.bucket_stats_url, headers=self.headers)
        assert resp.json == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": 0,
        }

    def test_buckets_stats_count_records(self):
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id_1 = resp.json['data']['id']
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id_2 = resp.json['data']['id']

        records_url = '%s/collections/%s/records' % (self.bucket_url,
                                                     collection_id_1)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)

        records_url = '%s/collections/%s/records' % (self.bucket_url,
                                                     collection_id_2)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)

        resp = self.app.get(self.bucket_stats_url, headers=self.headers)
        assert resp.json == {
            "collection_count": 2,
            "record_count": 5,
            "storage_size": EMPTY_RECORD_SIZE * 5,
        }

    def test_buckets_stats_updates_on_record_update(self):
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id_1 = resp.json['data']['id']
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id_2 = resp.json['data']['id']

        records_url = '%s/collections/%s/records' % (self.bucket_url,
                                                     collection_id_1)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)

        records_url = '%s/collections/%s/records' % (self.bucket_url,
                                                     collection_id_2)
        self.app.post(records_url,
                      headers=self.headers)
        resp = self.app.post(records_url,
                             headers=self.headers)

        record_url = '%s/collections/%s/records/%s' % (self.bucket_url,
                                                       collection_id_2,
                                                       resp.json['data']['id'])
        self.app.put_json(record_url,
                          {'data': {'foo': 'bar'}},
                          headers=self.headers)

        resp = self.app.get(self.bucket_stats_url, headers=self.headers)
        assert resp.json == {
            "collection_count": 2,
            "record_count": 5,
            "storage_size": EMPTY_RECORD_SIZE * 5 + len('"foo":"bar",'),
        }

    def test_buckets_stats_updates_on_record_delete(self):
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id_1 = resp.json['data']['id']
        resp = self.app.post(self.bucket_url + '/collections',
                             headers=self.headers)
        collection_id_2 = resp.json['data']['id']

        records_url = '%s/collections/%s/records' % (self.bucket_url,
                                                     collection_id_1)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)
        self.app.post(records_url,
                      headers=self.headers)

        records_url = '%s/collections/%s/records' % (self.bucket_url,
                                                     collection_id_2)
        self.app.post(records_url,
                      headers=self.headers)
        resp = self.app.post(records_url,
                             headers=self.headers)

        record_url = '%s/collections/%s/records/%s' % (self.bucket_url,
                                                       collection_id_2,
                                                       resp.json['data']['id'])
        self.app.delete(record_url,
                        headers=self.headers)

        resp = self.app.get(self.bucket_stats_url, headers=self.headers)
        assert resp.json == {
            "collection_count": 2,
            "record_count": 4,
            "storage_size": EMPTY_RECORD_SIZE * 5 - EMPTY_RECORD_SIZE,
        }
