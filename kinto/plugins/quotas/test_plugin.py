from kinto.core.errors import ERRORS
from kinto.tests.core.support import FormattedErrorMixin
from kinto.tests.support import BaseWebTest, unittest
from .utils import record_size, strip_stats_keys


class QuotaWebTest(BaseWebTest, unittest.TestCase):

    bucket_uri = '/buckets/test'
    collection_uri = '/buckets/test/collections/col'
    record_uri = '/buckets/test/collections/col/records/rec'
    group_uri = '/buckets/test/groups/grp'
    quota_uri = '/buckets/test'

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

    def get_app_settings(self, extra=None):
        settings = super(QuotaWebTest, self).get_app_settings(extra)
        settings['includes'] = 'kinto.plugins.quotas'
        return settings

    def assertStatsEqual(self, response, stats):
        data = response.json['data']
        for key in stats:
            assert data[key] == stats[key], data


class HelloViewTest(QuotaWebTest):

    def test_quota_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('quotas', capabilities)


class QuotaListenerTest(QuotaWebTest):

    #
    # Bucket
    #
    def test_stats_are_not_accessible_if_bucket_does_not_exists(self):
        self.app.get(self.quota_uri, headers=self.headers, status=403)

    def test_quota_tracks_bucket_creation(self):
        self.create_bucket()
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        })

    def test_tracks_bucket_attributes_update(self):
        self.create_bucket()
        body = {'data': {'foo': 'baz'}}
        resp = self.app.patch_json(self.bucket_uri, body,
                                   headers=self.headers)
        storage_size = record_size(strip_stats_keys(resp.json['data']))
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        })

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
    def test_stats_are_not_accessible_if_collection_does_not_exists(self):
        self.create_bucket()
        self.app.get(self.collection_uri, headers=self.headers, status=404)

    def test_quota_tracks_collection_creation(self):
        self.create_bucket()
        self.create_collection()

        # Bucket stats
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket) + record_size(self.collection)
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

        # Collection stats
        resp = self.app.get(self.collection_uri, headers=self.headers)
        storage_size = record_size(self.collection)
        self.assertStatsEqual(resp, {
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_tracks_collection_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'foo': 'baz'}}
        resp = self.app.patch_json(self.collection_uri, body,
                                   headers=self.headers)
        # Bucket stats
        storage_size = record_size(self.bucket)
        storage_size += record_size(strip_stats_keys(resp.json['data']))

        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

        # Collection stats
        resp = self.app.get(self.collection_uri, headers=self.headers)
        storage_size -= record_size(self.bucket)
        self.assertStatsEqual(resp, {
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_tracks_collection_delete(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'foo': 'baz'}}
        self.app.patch_json(self.collection_uri, body,
                            headers=self.headers)
        self.app.delete(self.collection_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        })

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
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(strip_stats_keys(self.bucket))
        })

    #
    # Group
    #

    def test_quota_tracks_group_creation(self):
        self.create_bucket()
        self.create_group()
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket) + record_size(self.group)
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_tracks_group_attributes_update(self):
        self.create_bucket()
        self.create_group()
        body = {'data': {'foo': 'baz', 'members': ['lui']}}
        resp = self.app.patch_json(self.group_uri, body,
                                   headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(resp.json['data'])
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_tracks_group_delete(self):
        self.create_bucket()
        self.create_group()
        self.app.delete(self.group_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        })

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
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

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
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_tracks_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

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
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })


class QuotaBucketMixin(object):
    def test_507_is_raised_if_quota_exceeded_on_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42}}
        resp = self.app.post_json('%s/records' % self.collection_uri,
                                  body, headers=self.headers, status=507)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            "There was not enough space to save the resource")

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_507_is_raised_if_quota_exceeded_on_collection_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42}}
        resp = self.app.post_json('%s/collections' % self.bucket_uri,
                                  body, headers=self.headers, status=507)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            "There was not enough space to save the resource")

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_507_is_raised_if_quota_exceeded_on_group_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'members': ['elle']}}
        resp = self.app.put_json(self.group_uri, body,
                                 headers=self.headers, status=507)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            "There was not enough space to save the resource")

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })


class QuotaMaxBytesExceededGlobalSettingsListenerTest(
        FormattedErrorMixin, QuotaBucketMixin, QuotaWebTest):
    def get_app_settings(self, extra=None):
        settings = super(QuotaMaxBytesExceededGlobalSettingsListenerTest,
                         self).get_app_settings(extra)
        settings['quotas.bucket_max_bytes'] = '150'
        return settings


class QuotaMaxBytesExceededSpecificSettingsListenerTest(
        FormattedErrorMixin, QuotaBucketMixin, QuotaWebTest):

    def get_app_settings(self, extra=None):
        settings = super(QuotaMaxBytesExceededSpecificSettingsListenerTest,
                         self).get_app_settings(extra)
        settings['quotas.bucket_test_max_bytes'] = '150'
        return settings


class QuotaCollectionMixin(object):
    quota_uri = '/buckets/test/collections/col'

    def test_507_is_raised_if_quota_exceeded_on_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42}}
        resp = self.app.post_json('%s/records' % self.collection_uri,
                                  body, headers=self.headers, status=507)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            "There was not enough space to save the resource")

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        storage_size += record_size(self.record)
        resp = self.app.get(self.quota_uri, headers=self.headers)
        self.assertStatsEqual(resp, {
            "record_count": 1,
            "storage_size": storage_size
        })


class QuotaMaxBytesExceededCollectionGlobalSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):
    def get_app_settings(self, extra=None):
        settings = super(
            QuotaMaxBytesExceededCollectionGlobalSettingsListenerTest,
            self).get_app_settings(extra)
        settings['quotas.collection_max_bytes'] = '100'
        return settings


class QuotaMaxBytesExceededCollectionBucketSpecificSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):

    def get_app_settings(self, extra=None):
        settings = super(
            QuotaMaxBytesExceededCollectionBucketSpecificSettingsListenerTest,
            self).get_app_settings(extra)
        settings['quotas.collection_test_max_bytes'] = '100'
        return settings


class QuotaMaxBytesExceededBucketCollectionSpecificSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):

    def get_app_settings(self, extra=None):
        settings = super(
            QuotaMaxBytesExceededBucketCollectionSpecificSettingsListenerTest,
            self).get_app_settings(extra)
        settings['quotas.collection_test_col_max_bytes'] = '100'
        return settings
