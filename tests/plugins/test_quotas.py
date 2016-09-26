import mock
import unittest

import transaction
import pytest
from pyramid import testing

from kinto import main as kinto_main
from kinto.core.errors import ERRORS
from kinto.core.storage.exceptions import RecordNotFoundError
from kinto.core.testing import FormattedErrorMixin, sqlalchemy, skip_if_no_statsd
from kinto.plugins.quotas.listener import (
    QUOTA_RESOURCE_NAME, QUOTA_BUCKET_ID, QUOTA_COLLECTION_ID)
from kinto.plugins.quotas.utils import record_size

from .. import support


class PluginSetup(unittest.TestCase):

    @skip_if_no_statsd
    def test_a_statsd_timer_is_used_for_quotas_if_configured(self):
        settings = {
            "statsd_url": "udp://127.0.0.1:8125",
            "includes": "kinto.plugins.quotas"
        }
        config = testing.setUp(settings=settings)
        with mock.patch('kinto.core.statsd.Client.timer') as mocked:
            kinto_main(None, config=config)
            mocked.assert_called_with('plugins.quotas')


class QuotaWebTest(support.BaseWebTest, unittest.TestCase):

    bucket_uri = '/buckets/test'
    collection_uri = '/buckets/test/collections/col'
    record_uri = '/buckets/test/collections/col/records/rec'
    group_uri = '/buckets/test/groups/grp'

    @classmethod
    def setUpClass(cls):
        if not sqlalchemy:
            raise unittest.SkipTest("postgresql is not installed.")

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

    def get_app_settings(self, extras=None):
        settings = super(QuotaWebTest, self).get_app_settings(extras)

        # Setup the postgresql backend for transaction support.
        settings['storage_backend'] = 'kinto.core.storage.postgresql'
        db = "postgres://postgres:postgres@localhost/testdb"
        settings['storage_url'] = db
        settings['permission_backend'] = 'kinto.core.permission.postgresql'
        settings['permission_url'] = db
        settings['cache_backend'] = 'kinto.core.cache.memory'

        settings['includes'] = 'kinto.plugins.quotas'
        return settings

    def assertStatsEqual(self, data, stats):
        for key in stats:
            assert data[key] == stats[key]


class HelloViewTest(QuotaWebTest):

    def test_quota_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('quotas', capabilities)


class QuotaListenerTest(QuotaWebTest):

    #
    # Bucket
    #
    def test_quota_tracks_bucket_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_tracks_bucket_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 'baz'}}
        resp = self.app.patch_json(self.bucket_uri, body,
                                   headers=self.headers)
        storage_size = record_size(resp.json['data'])
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_bucket_delete_destroys_its_quota_entries(self):
        self.create_bucket()
        self.app.delete(self.bucket_uri, headers=self.headers)
        stored_in_backend, _ = self.storage.get_all(
            parent_id='/buckets/test',
            collection_id=QUOTA_RESOURCE_NAME)
        assert len(stored_in_backend) == 0

    def test_bucket_delete_doesnt_raise_if_quota_entries_do_not_exist(self):
        self.create_bucket()
        self.storage.delete(parent_id='/buckets/test',
                            collection_id=QUOTA_RESOURCE_NAME,
                            object_id=QUOTA_BUCKET_ID)
        transaction.commit()
        self.app.delete(self.bucket_uri, headers=self.headers)

    #
    # Collection
    #
    def test_stats_are_not_accessible_if_collection_does_not_exist(self):
        self.create_bucket()
        self.app.get(self.collection_uri, headers=self.headers, status=404)

    def test_quota_tracks_collection_creation(self):
        self.create_bucket()
        self.create_collection()

        # Bucket stats
        storage_size = record_size(self.bucket) + record_size(self.collection)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

        # Collection stats
        storage_size = record_size(self.collection)
        data = self.storage.get(QUOTA_RESOURCE_NAME, self.collection_uri,
                                QUOTA_COLLECTION_ID)
        self.assertStatsEqual(data, {
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
        storage_size += record_size(resp.json['data'])

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

        # Collection stats
        storage_size -= record_size(self.bucket)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.collection_uri,
                                object_id=QUOTA_COLLECTION_ID)
        self.assertStatsEqual(data, {
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
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        })

    def test_collection_delete_destroys_its_quota_entries(self):
        self.create_bucket()
        self.create_collection()
        self.app.delete(self.collection_uri, headers=self.headers)
        stored_in_backend, _ = self.storage.get_all(
            parent_id=self.collection_uri,
            collection_id=QUOTA_RESOURCE_NAME)
        assert len(stored_in_backend) == 0

    def test_collection_delete_doesnt_raise_if_quota_entries_dont_exist(self):
        self.create_bucket()
        self.create_collection()
        self.storage.delete(parent_id=self.collection_uri,
                            collection_id=QUOTA_RESOURCE_NAME,
                            object_id=QUOTA_COLLECTION_ID)
        transaction.commit()
        self.app.delete(self.collection_uri, headers=self.headers)

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
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        })

    #
    # Group
    #

    def test_quota_tracks_group_creation(self):
        self.create_bucket()
        self.create_group()
        storage_size = record_size(self.bucket) + record_size(self.group)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
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
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_tracks_group_delete(self):
        self.create_bucket()
        self.create_group()
        self.app.delete(self.group_uri, headers=self.headers)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
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
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
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
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_tracks_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
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
        storage_size = record_size(self.bucket) + record_size(self.collection)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_bulk_create(self):
        body = {
            'defaults': {
                'method': 'POST',
                'path': '%s/records' % self.collection_uri,
            },
            'requests': [{
                'path': self.bucket_uri,
                'method': 'PUT'
            }, {
                'path': self.collection_uri,
                'method': 'PUT'
            }, {
                'body': {'data': {'id': 'a', 'attr': 1}},
            }, {
                'body': {'data': {'id': 'b', 'attr': 2}},
            }, {
                'body': {'data': {'id': 'c', 'attr': 3}}
            }]
        }
        self.app.post_json('/batch', body, headers=self.headers)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 3,
            "storage_size": 232
        })

    def test_bulk_update(self):
        body = {
            'defaults': {
                'method': 'POST',
                'path': '%s/collections' % self.bucket_uri,
            },
            'requests': [{
                'path': self.bucket_uri,
                'method': 'PUT'
            }, {
                'body': {'data': {'id': 'a', 'attr': 10}},
            }, {
                'body': {'data': {'id': 'b', 'attr': 200}},
            }, {
                'body': {'data': {'id': 'c', 'attr': 3000}}
            }]
        }
        self.app.post_json('/batch', body, headers=self.headers)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 3,
            "record_count": 0,
            "storage_size": 196
        })
        body = {
            'defaults': {
                'method': 'PUT',
            },
            'requests': [{
                'path': '%s/collections/a' % self.bucket_uri,
                'body': {'data': {'attr': 100}},
            }, {
                'path': '%s/collections/b' % self.bucket_uri,
                'body': {'data': {'attr': 2000}},
            }, {
                'path': '%s/collections/c' % self.bucket_uri,
                'body': {'data': {'attr': 30000}}
            }]
        }
        self.app.post_json('/batch', body, headers=self.headers)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 3,
            "record_count": 0,
            "storage_size": 199
        })

    def test_bulk_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()

        body = {
            'defaults': {
                'method': 'POST',
                'path': '%s/collections' % self.bucket_uri,
            },
            'requests': [{
                'body': {'data': {'id': 'a', 'attr': 1}},
            }, {
                'body': {'data': {'id': 'b', 'attr': 2}},
            }, {
                'body': {'data': {'id': 'c', 'attr': 3}}
            }]
        }
        self.app.post_json('/batch', body, headers=self.headers)

        body = {
            'defaults': {
                'method': 'DELETE',
            },
            'requests': [{
                'path': '%s/collections/a' % self.bucket_uri
            }, {
                'path': '%s/collections/b' % self.bucket_uri
            }, {
                'path': '%s/collections/c' % self.bucket_uri
            }, {
                'path': self.collection_uri
            }]
        }
        self.app.post_json('/batch', body, headers=self.headers)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": record_size(self.bucket)
        })

        with pytest.raises(RecordNotFoundError):
            self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                             parent_id='%s/collections/a' % self.bucket_uri,
                             object_id=QUOTA_COLLECTION_ID)

        with pytest.raises(RecordNotFoundError):
            self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                             parent_id='%s/collections/b' % self.bucket_uri,
                             object_id=QUOTA_COLLECTION_ID)

        with pytest.raises(RecordNotFoundError):
            self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                             parent_id='%s/collections/c' % self.bucket_uri,
                             object_id=QUOTA_COLLECTION_ID)

        with pytest.raises(RecordNotFoundError):
            self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                             parent_id=self.collection_uri,
                             object_id=QUOTA_COLLECTION_ID)


class QuotaBucketRecordMixin(object):
    def test_507_is_raised_if_quota_exceeded_on_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42}}
        resp = self.app.post_json('%s/records' % self.collection_uri,
                                  body, headers=self.headers, status=507)

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

        # Check that the record wasn't created
        resp = self.app.get('%s/records' % self.collection_uri,
                            headers=self.headers)
        assert len(resp.json['data']) == 1


class QuotaBucketUpdateMixin(object):
    def test_507_is_raised_if_quota_exceeded_on_record_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42, 'bar': 'This is a very long string.'}}
        resp = self.app.patch_json(self.record_uri,
                                   body, headers=self.headers, status=507)

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_507_is_raised_if_quota_exceeded_on_collection_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42, 'bar': 'This is a very long string.'}}
        resp = self.app.patch_json(self.collection_uri,
                                   body, headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_507_is_raised_if_quota_exceeded_on_group_update(self):
        self.create_bucket()
        self.create_collection()
        body = {'data': {'members': []}}
        resp = self.app.put_json(self.group_uri, body,
                                 headers=self.headers)
        group = resp.json['data']
        body = {'data': {'members': ['elle', 'lui', 'je', 'tu', 'il', 'nous',
                                     'vous', 'ils', 'elles']}}
        resp = self.app.put_json(self.group_uri, body,
                                 headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(group)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_507_is_not_raised_if_quota_exceeded_on_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_507_is_not_raised_if_quota_exceeded_on_collection_delete(self):
        self.create_bucket()
        self.create_collection()
        # fake the quota to the Max
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        data['storage_size'] = 140
        self.storage.update(collection_id=QUOTA_RESOURCE_NAME,
                            parent_id=self.bucket_uri,
                            object_id=QUOTA_BUCKET_ID,
                            record=data)
        transaction.commit()
        self.app.delete(self.collection_uri,
                        headers=self.headers)

        storage_size = 140
        storage_size -= record_size(self.collection)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        })

    def test_507_is_raised_if_quota_exceeded_on_group_delete(self):
        self.create_bucket()
        body = {"data": {"members": []}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        group = resp.json['data']
        # fake the quota to the Max
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        data['storage_size'] = 140
        self.storage.update(collection_id=QUOTA_RESOURCE_NAME,
                            parent_id=self.bucket_uri,
                            object_id=QUOTA_BUCKET_ID,
                            record=data)
        transaction.commit()

        self.app.delete(self.group_uri, headers=self.headers)

        storage_size = 140
        storage_size -= record_size(group)
        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 0,
            "record_count": 0,
            "storage_size": storage_size
        })


class QuotaBucketMixin(object):
    def test_507_is_raised_if_quota_exceeded_on_collection_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42}}
        resp = self.app.post_json('%s/collections' % self.bucket_uri,
                                  body, headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

        # Check that the collection wasn't created
        resp = self.app.get('%s/collections' % self.bucket_uri,
                            headers=self.headers)
        assert len(resp.json['data']) == 1

    def test_507_is_raised_if_quota_exceeded_on_group_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'members': ['elle']}}
        resp = self.app.put_json(self.group_uri, body,
                                 headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(collection_id=QUOTA_RESOURCE_NAME,
                                parent_id=self.bucket_uri,
                                object_id=QUOTA_BUCKET_ID)
        self.assertStatsEqual(data, {
            "collection_count": 1,
            "record_count": 1,
            "storage_size": storage_size
        })

        # Check that the group wasn't created
        resp = self.app.get('%s/groups' % self.bucket_uri,
                            headers=self.headers)
        assert len(resp.json['data']) == 0


class QuotaMaxBytesExceededSettingsListenerTest(
        FormattedErrorMixin, QuotaBucketRecordMixin, QuotaBucketUpdateMixin,
        QuotaBucketMixin, QuotaWebTest):

    error_message = "Bucket maximum total size exceeded "

    def get_app_settings(self, extras=None):
        settings = super(QuotaMaxBytesExceededSettingsListenerTest,
                         self).get_app_settings(extras)
        settings['quotas.bucket_max_bytes'] = '150'
        return settings


class QuotaMaxBytesExceededBucketSettingsListenerTest(
        FormattedErrorMixin, QuotaBucketRecordMixin, QuotaBucketUpdateMixin,
        QuotaBucketMixin, QuotaWebTest):

    error_message = "Bucket maximum total size exceeded "

    def get_app_settings(self, extras=None):
        settings = super(QuotaMaxBytesExceededBucketSettingsListenerTest,
                         self).get_app_settings(extras)
        settings['quotas.bucket_test_max_bytes'] = '150'
        return settings


class QuotaMaxItemsExceededSettingsListenerTest(
        FormattedErrorMixin, QuotaBucketRecordMixin, QuotaWebTest):

    error_message = "Bucket maximum number of objects exceeded "

    def get_app_settings(self, extras=None):
        settings = super(QuotaMaxItemsExceededSettingsListenerTest,
                         self).get_app_settings(extras)
        settings['quotas.bucket_max_items'] = '1'
        return settings


class QuotaMaxItemsExceededBucketSettingsListenerTest(
        FormattedErrorMixin, QuotaBucketRecordMixin, QuotaWebTest):

    error_message = "Bucket maximum number of objects exceeded "

    def get_app_settings(self, extras=None):
        settings = super(QuotaMaxItemsExceededBucketSettingsListenerTest,
                         self).get_app_settings(extras)
        settings['quotas.bucket_test_max_items'] = '1'
        return settings


class QuotaMaxBytesPerItemExceededListenerTest(
        FormattedErrorMixin, QuotaBucketRecordMixin, QuotaBucketUpdateMixin,
        QuotaBucketMixin, QuotaWebTest):

    error_message = "Maximum bytes per object exceeded "

    def get_app_settings(self, extras=None):
        settings = super(QuotaMaxBytesPerItemExceededListenerTest,
                         self).get_app_settings(extras)
        settings['quotas.bucket_max_bytes_per_item'] = '55'
        return settings


class QuotaMaxBytesPerItemExceededBucketListenerTest(
        FormattedErrorMixin, QuotaBucketRecordMixin, QuotaBucketUpdateMixin,
        QuotaBucketMixin, QuotaWebTest):

    error_message = "Maximum bytes per object exceeded "

    def get_app_settings(self, extras=None):
        settings = super(QuotaMaxBytesPerItemExceededBucketListenerTest,
                         self).get_app_settings(extras)
        settings['quotas.bucket_test_max_bytes_per_item'] = '55'
        return settings


class QuotaCollectionMixin(object):
    def test_507_is_raised_if_quota_exceeded_on_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42}}
        resp = self.app.post_json('%s/records' % self.collection_uri,
                                  body, headers=self.headers, status=507)

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(QUOTA_RESOURCE_NAME, self.collection_uri,
                                QUOTA_COLLECTION_ID)
        self.assertStatsEqual(data, {
            "record_count": 1,
            "storage_size": storage_size
        })


class QuotaCollectionUpdateMixin(object):
    def test_507_is_raised_if_quota_exceeded_on_record_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {'data': {'foo': 42, 'bar': 'This is a very long string.'}}
        resp = self.app.patch_json(self.record_uri,
                                   body, headers=self.headers, status=507)

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage",
            self.error_message)

        data = self.storage.get(QUOTA_RESOURCE_NAME, self.collection_uri,
                                QUOTA_COLLECTION_ID)
        self.assertStatsEqual(data, {
            "record_count": 1,
            "storage_size": storage_size
        })

    def test_507_is_not_raised_if_quota_exceeded_on_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        data = self.storage.get(QUOTA_RESOURCE_NAME, self.collection_uri,
                                QUOTA_COLLECTION_ID)
        self.assertStatsEqual(data, {
            "record_count": 0,
            "storage_size": storage_size
        })


class QuotaMaxBytesExceededCollectionSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin,
        QuotaWebTest):

    error_message = "Collection maximum size exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxBytesExceededCollectionSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_max_bytes'] = '100'
        return settings


class QuotaMaxBytesExceededCollectionBucketSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin,
        QuotaWebTest):

    error_message = "Collection maximum size exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxBytesExceededCollectionBucketSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_test_max_bytes'] = '100'
        return settings


class QuotaMaxBytesExceededBucketCollectionSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin,
        QuotaWebTest):

    error_message = "Collection maximum size exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxBytesExceededBucketCollectionSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_test_col_max_bytes'] = '100'
        return settings


class QuotaMaxItemsExceededCollectionSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):

    error_message = "Collection maximum number of objects exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxItemsExceededCollectionSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_max_items'] = '1'
        return settings


class QuotaMaxItemsExceededCollectionBucketSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):

    error_message = "Collection maximum number of objects exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxItemsExceededCollectionBucketSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_test_max_items'] = '1'
        return settings


class QuotaMaxItemsExceededBucketCollectionSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):

    error_message = "Collection maximum number of objects exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxItemsExceededBucketCollectionSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_test_col_max_items'] = '1'
        return settings


class QuotaMaxBytesPerItemExceededCollectionSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest):

    error_message = "Maximum bytes per object exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxBytesPerItemExceededCollectionSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_max_bytes_per_item'] = '80'
        return settings


class QuotaMaxBytesPerItemExceededCollectionBucketSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin,
        QuotaWebTest):

    error_message = "Maximum bytes per object exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxBytesPerItemExceededCollectionBucketSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_test_max_bytes_per_item'] = '80'
        return settings


class QuotaMaxBytesPerItemExceededBucketCollectionSettingsListenerTest(
        FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin,
        QuotaWebTest):

    error_message = "Maximum bytes per object exceeded "

    def get_app_settings(self, extras=None):
        settings = super(
            QuotaMaxBytesPerItemExceededBucketCollectionSettingsListenerTest,
            self).get_app_settings(extras)
        settings['quotas.collection_test_col_max_bytes_per_item'] = '80'
        return settings
