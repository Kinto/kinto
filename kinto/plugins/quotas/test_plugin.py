import mock
import re

from kinto.tests.support import (BaseWebTest, unittest, get_user_headers)
from .utils import record_size


class QuotaWebTest(BaseWebTest, unittest.TestCase):

    def get_app_settings(self, extra=None):
        settings = super(QuotaWebTest, self).get_app_settings(extra)
        settings['includes'] = 'kinto.plugins.quotas'
        return settings


class HelloViewTest(QuotaWebTest):

    def test_quota_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('quotas', capabilities)


class QuotaListenerTest(QuotaWebTest):

    bucket_uri = '/buckets/test'
    collection_uri = '/buckets/test/collections/col'
    record_uri = '/buckets/test/collections/col/records/rec'
    group_uri = '/buckets/test/groups/grp'
    quota_uri = '/buckets/test/stats'

    def create_bucket(self):
        resp = self.app.put(self.bucket_uri, headers=self.headers)
        self.bucket = resp.json['data']

    def create_collection(self):
        resp = self.app.put(self.collection_uri, headers=self.headers)
        self.collection = resp.json['data']

    def create_group(self):
        body = {'data': {'members': ['elle']}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        self.group = resp.json['data']

    def create_record(self):
        body = {'data': {'foo': 42}}
        resp = self.app.put_json(self.record_uri, body, headers=self.headers)
        self.record = resp.json['data']

    def test_only_get_on_collection_is_allowed(self):
        self.app.post(self.quota_uri, headers=self.headers, status=405)
        self.app.put(self.quota_uri, headers=self.headers, status=405)
        self.app.patch(self.quota_uri, headers=self.headers, status=405)
        self.app.delete(self.quota_uri, headers=self.headers, status=405)

    #
    # Bucket
    #
    def test_stats_are_not_accessible_if_bucket_does_not_exists(self):
        self.app.get(self.quota_uri, headers=self.headers, status=403)

    def test_quota_tracks_bucket_creation(self):
        self.create_bucket()
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        }

    def test_tracks_bucket_attributes_update(self):
        self.create_bucket()
        body = {'data': {'foo': 'baz'}}
        resp = self.app.patch_json(self.bucket_uri, body,
                                   headers=self.headers)
        storage_size = record_size(resp.json['data'])
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        }

    def test_bucket_delete_destroys_its_quota_entries(self):
        self.create_bucket()
        self.app.delete(self.bucket_uri, headers=self.headers)
        storage = self.app.app.registry.storage
        stored_in_backend, _ = storage.get_all(parent_id='/buckets/test',
                                               collection_id='quota')
        assert len(stored_in_backend) == 0

    #
    # Collection
    #

    def test_quota_tracks_collection_creation(self):
        self.create_bucket()
        self.create_collection()
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket) + record_size(self.collection)
        assert resp.json['data'] == {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        }

    def test_tracks_collection_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'foo': 'baz'}}
        resp = self.app.patch_json(self.collection_uri, body,
                                   headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(resp.json['data'])
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        }

    def test_tracks_collection_delete(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'foo': 'baz'}}
        self.app.patch_json(self.collection_uri, body,
                            headers=self.headers)
        self.app.delete(self.collection_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        }

    def test_tracks_collection_delete_with_multiple_records(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'foo': 42}}
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.delete(self.collection_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        }

    #
    # Group
    #

    def test_quota_tracks_group_creation(self):
        self.create_bucket()
        self.create_group()
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket) + record_size(self.group)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        }

    def test_tracks_group_attributes_update(self):
        self.create_bucket()
        self.create_group()
        body = {'data': {'foo': 'baz', 'members': ['lui']}}
        resp = self.app.patch_json(self.group_uri, body,
                                   headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(resp.json['data'])
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        }

    def test_tracks_group_delete(self):
        self.create_bucket()
        self.create_group()
        self.app.delete(self.group_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        }

    #
    # Record
    #

    def test_quota_tracks_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        assert resp.json['data'] == {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        }

    def test_tracks_record_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        resp = self.app.patch_json(self.record_uri, {'data': {'foo': 'baz'}},
                                   headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(resp.json['data'])
        resp = self.app.get(self.quota_uri, headers=self.headers)
        assert resp.json['data'] == {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        }

    def test_tracks_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        assert resp.json['data'] == {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        }

    def test_tracks_records_delete_with_multiple_records(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'foo': 42}}
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.post_json('%s/records' % self.collection_uri,
                           body, headers=self.headers)
        self.app.delete('%s/records' % self.collection_uri,
                        headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket) + record_size(self.collection)
        assert resp.json['data'] == {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        }


class QuotaExceededListenerTest(QuotaWebTest):
    pass
