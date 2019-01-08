import unittest
from unittest import mock

import transaction
import pytest
from pyramid import testing

from kinto import main as kinto_main
from kinto.core.errors import ERRORS
from kinto.core.storage import Sort
from kinto.core.storage.exceptions import ObjectNotFoundError
from kinto.core.testing import FormattedErrorMixin, sqlalchemy, skip_if_no_statsd
from kinto.plugins.quotas import scripts
from kinto.plugins.quotas.listener import (
    QUOTA_RESOURCE_NAME,
    BUCKET_QUOTA_OBJECT_ID,
    COLLECTION_QUOTA_OBJECT_ID,
)
from kinto.plugins.quotas.utils import record_size

from .. import support


class PluginSetup(unittest.TestCase):
    @skip_if_no_statsd
    def test_a_statsd_timer_is_used_for_quotas_if_configured(self):
        settings = {
            "statsd_url": "udp://127.0.0.1:8125",
            "includes": "kinto.plugins.quotas",
            "storage_strict_json": True,
        }
        config = testing.setUp(settings=settings)
        with mock.patch("kinto.core.statsd.Client.timer") as mocked:
            kinto_main(None, config=config)
            mocked.assert_called_with("plugins.quotas")


class QuotaWebTest(support.BaseWebTest, unittest.TestCase):

    bucket_uri = "/buckets/test"
    collection_uri = "/buckets/test/collections/col"
    record_uri = "/buckets/test/collections/col/records/rec"
    group_uri = "/buckets/test/groups/grp"

    @classmethod
    def setUpClass(cls):
        if not sqlalchemy:
            raise unittest.SkipTest("postgresql is not installed.")
        super().setUpClass()

    def create_bucket(self):
        resp = self.app.put(self.bucket_uri, headers=self.headers)
        self.bucket = resp.json["data"]

    def create_collection(self):
        resp = self.app.put(self.collection_uri, headers=self.headers)
        self.collection = resp.json["data"]

    def create_group(self):
        body = {"data": {"members": ["elle"]}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        self.group = resp.json["data"]

    def create_record(self):
        body = {"data": {"foo": 42}}
        resp = self.app.put_json(self.record_uri, body, headers=self.headers)
        self.record = resp.json["data"]

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)

        # Setup the postgresql backend for transaction support.
        settings["storage_backend"] = "kinto.core.storage.postgresql"
        db = "postgresql://postgres:postgres@localhost/testdb"
        settings["storage_url"] = db
        settings["permission_backend"] = "kinto.core.permission.postgresql"
        settings["permission_url"] = db
        settings["cache_backend"] = "kinto.core.cache.memory"

        settings["includes"] = "kinto.plugins.quotas"
        return settings

    def assertStatsEqual(self, data, stats):
        for key in stats:
            assert data[key] == stats[key]


class HelloViewTest(QuotaWebTest):
    def test_quota_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("quotas", capabilities)


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
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

    def test_tracks_bucket_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": "baz"}}
        resp = self.app.patch_json(self.bucket_uri, body, headers=self.headers)
        storage_size = record_size(resp.json["data"])
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

    def test_delete_all_buckets_destroys_all_quota_entries(self):
        self.app.put("/buckets/a", headers=self.headers)
        self.app.put("/buckets/b", headers=self.headers)

        self.app.delete("/buckets", headers=self.headers)

        stored_in_backend = self.storage.list_all(
            parent_id="/buckets/*", resource_name=QUOTA_RESOURCE_NAME
        )
        assert len(stored_in_backend) == 0

    def test_bucket_delete_destroys_its_quota_entries(self):
        self.create_bucket()
        self.app.delete(self.bucket_uri, headers=self.headers)
        stored_in_backend = self.storage.list_all(
            parent_id="/buckets/test", resource_name=QUOTA_RESOURCE_NAME
        )
        assert len(stored_in_backend) == 0

    def test_bucket_delete_doesnt_raise_if_quota_entries_do_not_exist(self):
        self.create_bucket()
        self.storage.delete(
            parent_id="/buckets/test",
            resource_name=QUOTA_RESOURCE_NAME,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
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
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 0, "storage_size": storage_size}
        )

        # Collection stats
        storage_size = record_size(self.collection)
        data = self.storage.get(
            QUOTA_RESOURCE_NAME, self.collection_uri, COLLECTION_QUOTA_OBJECT_ID
        )
        self.assertStatsEqual(data, {"record_count": 0, "storage_size": storage_size})

    def test_tracks_collection_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        body = {"data": {"foo": "baz"}}
        resp = self.app.patch_json(self.collection_uri, body, headers=self.headers)
        # Bucket stats
        storage_size = record_size(self.bucket)
        storage_size += record_size(resp.json["data"])

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 0, "storage_size": storage_size}
        )

        # Collection stats
        storage_size -= record_size(self.bucket)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.collection_uri,
            object_id=COLLECTION_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(data, {"record_count": 0, "storage_size": storage_size})

    def test_tracks_collection_delete(self):
        self.create_bucket()
        self.create_collection()
        body = {"data": {"foo": "baz"}}
        self.app.patch_json(self.collection_uri, body, headers=self.headers)
        self.app.delete(self.collection_uri, headers=self.headers)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data,
            {"collection_count": 0, "record_count": 0, "storage_size": record_size(self.bucket)},
        )

    def test_collection_delete_destroys_its_quota_entries(self):
        self.create_bucket()
        self.create_collection()
        self.app.delete(self.collection_uri, headers=self.headers)
        stored_in_backend = self.storage.list_all(
            parent_id=self.collection_uri, resource_name=QUOTA_RESOURCE_NAME
        )
        assert len(stored_in_backend) == 0

    def test_collection_delete_doesnt_raise_if_quota_entries_dont_exist(self):
        self.create_bucket()
        self.create_collection()
        self.storage.delete(
            parent_id=self.collection_uri,
            resource_name=QUOTA_RESOURCE_NAME,
            object_id=COLLECTION_QUOTA_OBJECT_ID,
        )
        transaction.commit()
        self.app.delete(self.collection_uri, headers=self.headers)

    def test_tracks_collection_delete_with_multiple_records(self):
        self.create_bucket()
        self.create_collection()
        body = {"data": {"foo": 42}}
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.delete(self.collection_uri, headers=self.headers)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data,
            {"collection_count": 0, "record_count": 0, "storage_size": record_size(self.bucket)},
        )

    #
    # Group
    #

    def test_quota_tracks_group_creation(self):
        self.create_bucket()
        self.create_group()
        storage_size = record_size(self.bucket) + record_size(self.group)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 0, "record_count": 0, "storage_size": storage_size}
        )

    def test_tracks_group_attributes_update(self):
        self.create_bucket()
        self.create_group()
        body = {"data": {"foo": "baz", "members": ["lui"]}}
        resp = self.app.patch_json(self.group_uri, body, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(resp.json["data"])
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 0, "record_count": 0, "storage_size": storage_size}
        )

    def test_tracks_group_delete(self):
        self.create_bucket()
        self.create_group()
        self.app.delete(self.group_uri, headers=self.headers)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data,
            {"collection_count": 0, "record_count": 0, "storage_size": record_size(self.bucket)},
        )

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
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

    def test_tracks_record_attributes_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        resp = self.app.patch_json(self.record_uri, {"data": {"foo": "baz"}}, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(resp.json["data"])
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

    def test_tracks_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 0, "storage_size": storage_size}
        )

    def test_tracks_records_delete_with_multiple_records(self):
        self.create_bucket()
        self.create_collection()
        body = {"data": {"foo": 42}}
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.post_json("{}/records".format(self.collection_uri), body, headers=self.headers)
        self.app.delete("{}/records".format(self.collection_uri), headers=self.headers)
        storage_size = record_size(self.bucket) + record_size(self.collection)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 0, "storage_size": storage_size}
        )

    def test_bulk_create(self):
        body = {
            "defaults": {"method": "POST", "path": "{}/records".format(self.collection_uri)},
            "requests": [
                {"path": self.bucket_uri, "method": "PUT"},
                {"path": self.collection_uri, "method": "PUT"},
                {"body": {"data": {"id": "a", "attr": 1}}},
                {"body": {"data": {"id": "b", "attr": 2}}},
                {"body": {"data": {"id": "c", "attr": 3}}},
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 3, "storage_size": 232}
        )

    def test_bulk_update(self):
        body = {
            "defaults": {"method": "POST", "path": "{}/collections".format(self.bucket_uri)},
            "requests": [
                {"path": self.bucket_uri, "method": "PUT"},
                {"body": {"data": {"id": "a", "attr": 10}}},
                {"body": {"data": {"id": "b", "attr": 200}}},
                {"body": {"data": {"id": "c", "attr": 3000}}},
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 3, "record_count": 0, "storage_size": 196}
        )
        body = {
            "defaults": {"method": "PUT"},
            "requests": [
                {
                    "path": "{}/collections/a".format(self.bucket_uri),
                    "body": {"data": {"attr": 100}},
                },
                {
                    "path": "{}/collections/b".format(self.bucket_uri),
                    "body": {"data": {"attr": 2000}},
                },
                {
                    "path": "{}/collections/c".format(self.bucket_uri),
                    "body": {"data": {"attr": 30000}},
                },
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 3, "record_count": 0, "storage_size": 199}
        )

    def test_bulk_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()

        body = {
            "defaults": {"method": "POST", "path": "{}/collections".format(self.bucket_uri)},
            "requests": [
                {"body": {"data": {"id": "a", "attr": 1}}},
                {"body": {"data": {"id": "b", "attr": 2}}},
                {"body": {"data": {"id": "c", "attr": 3}}},
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)

        body = {
            "defaults": {"method": "DELETE"},
            "requests": [
                {"path": "{}/collections/a".format(self.bucket_uri)},
                {"path": "{}/collections/b".format(self.bucket_uri)},
                {"path": "{}/collections/c".format(self.bucket_uri)},
                {"path": self.collection_uri},
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data,
            {"collection_count": 0, "record_count": 0, "storage_size": record_size(self.bucket)},
        )

        with pytest.raises(ObjectNotFoundError):
            self.storage.get(
                resource_name=QUOTA_RESOURCE_NAME,
                parent_id="{}/collections/a".format(self.bucket_uri),
                object_id=COLLECTION_QUOTA_OBJECT_ID,
            )

        with pytest.raises(ObjectNotFoundError):
            self.storage.get(
                resource_name=QUOTA_RESOURCE_NAME,
                parent_id="{}/collections/b".format(self.bucket_uri),
                object_id=COLLECTION_QUOTA_OBJECT_ID,
            )

        with pytest.raises(ObjectNotFoundError):
            self.storage.get(
                resource_name=QUOTA_RESOURCE_NAME,
                parent_id="{}/collections/c".format(self.bucket_uri),
                object_id=COLLECTION_QUOTA_OBJECT_ID,
            )

        with pytest.raises(ObjectNotFoundError):
            self.storage.get(
                resource_name=QUOTA_RESOURCE_NAME,
                parent_id=self.collection_uri,
                object_id=COLLECTION_QUOTA_OBJECT_ID,
            )


class QuotaBucketRecordMixin:
    def test_507_is_raised_if_quota_exceeded_on_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": 42}}
        resp = self.app.post_json(
            "{}/records".format(self.collection_uri), body, headers=self.headers, status=507
        )

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

        # Check that the record wasn't created
        resp = self.app.get("{}/records".format(self.collection_uri), headers=self.headers)
        assert len(resp.json["data"]) == 1


class QuotaBucketUpdateMixin:
    def test_507_is_raised_if_quota_exceeded_on_record_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": 42, "bar": "This is a very long string."}}
        resp = self.app.patch_json(self.record_uri, body, headers=self.headers, status=507)

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

    def test_507_is_raised_if_quota_exceeded_on_collection_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": 42, "bar": "This is a very long string."}}
        resp = self.app.patch_json(self.collection_uri, body, headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

    def test_507_is_raised_if_quota_exceeded_on_group_update(self):
        self.create_bucket()
        self.create_collection()
        body = {"data": {"members": []}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        group = resp.json["data"]
        body = {
            "data": {"members": ["elle", "lui", "je", "tu", "il", "nous", "vous", "ils", "elles"]}
        }
        resp = self.app.put_json(self.group_uri, body, headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(group)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 0, "storage_size": storage_size}
        )

    def test_507_is_not_raised_if_quota_exceeded_on_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)

        # Check that the storage was not updated.
        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 0, "storage_size": storage_size}
        )

    def test_507_is_not_raised_if_quota_exceeded_on_collection_delete(self):
        self.create_bucket()
        self.create_collection()
        # fake the quota to the Max
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        data["storage_size"] = 140
        self.storage.update(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
            obj=data,
        )
        transaction.commit()
        self.app.delete(self.collection_uri, headers=self.headers)

        storage_size = 140
        storage_size -= record_size(self.collection)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 0, "record_count": 0, "storage_size": storage_size}
        )

    def test_507_is_raised_if_quota_exceeded_on_group_delete(self):
        self.create_bucket()
        body = {"data": {"members": []}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        group = resp.json["data"]
        # fake the quota to the Max
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        data["storage_size"] = 140
        self.storage.update(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
            obj=data,
        )
        transaction.commit()

        self.app.delete(self.group_uri, headers=self.headers)

        storage_size = 140
        storage_size -= record_size(group)
        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 0, "record_count": 0, "storage_size": storage_size}
        )


class QuotaBucketMixin:
    def test_507_is_raised_if_quota_exceeded_on_collection_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": 42}}
        resp = self.app.post_json(
            "{}/collections".format(self.bucket_uri), body, headers=self.headers, status=507
        )

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

        # Check that the collection wasn't created
        resp = self.app.get("{}/collections".format(self.bucket_uri), headers=self.headers)
        assert len(resp.json["data"]) == 1

    def test_507_is_raised_if_quota_exceeded_on_group_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"members": ["elle"]}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers, status=507)

        storage_size = record_size(self.bucket)
        storage_size += record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            resource_name=QUOTA_RESOURCE_NAME,
            parent_id=self.bucket_uri,
            object_id=BUCKET_QUOTA_OBJECT_ID,
        )
        self.assertStatsEqual(
            data, {"collection_count": 1, "record_count": 1, "storage_size": storage_size}
        )

        # Check that the group wasn't created
        resp = self.app.get("{}/groups".format(self.bucket_uri), headers=self.headers)
        assert len(resp.json["data"]) == 0


class QuotaMaxBytesExceededSettingsListenerTest(
    FormattedErrorMixin,
    QuotaBucketRecordMixin,
    QuotaBucketUpdateMixin,
    QuotaBucketMixin,
    QuotaWebTest,
):

    error_message = "Bucket maximum total size exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.bucket_max_bytes"] = "150"
        return settings


class QuotaMaxBytesExceededBucketSettingsListenerTest(
    FormattedErrorMixin,
    QuotaBucketRecordMixin,
    QuotaBucketUpdateMixin,
    QuotaBucketMixin,
    QuotaWebTest,
):

    error_message = "Bucket maximum total size exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.bucket_test_max_bytes"] = "150"
        return settings


class QuotaMaxItemsExceededSettingsListenerTest(
    FormattedErrorMixin, QuotaBucketRecordMixin, QuotaWebTest
):

    error_message = "Bucket maximum number of objects exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.bucket_max_items"] = "1"
        return settings


class QuotaMaxItemsExceededBucketSettingsListenerTest(
    FormattedErrorMixin, QuotaBucketRecordMixin, QuotaWebTest
):

    error_message = "Bucket maximum number of objects exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.bucket_test_max_items"] = "1"
        return settings


class QuotaMaxBytesPerItemExceededListenerTest(
    FormattedErrorMixin,
    QuotaBucketRecordMixin,
    QuotaBucketUpdateMixin,
    QuotaBucketMixin,
    QuotaWebTest,
):

    error_message = "Maximum bytes per object exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.bucket_max_bytes_per_item"] = "55"
        return settings


class QuotaMaxBytesPerItemExceededBucketListenerTest(
    FormattedErrorMixin,
    QuotaBucketRecordMixin,
    QuotaBucketUpdateMixin,
    QuotaBucketMixin,
    QuotaWebTest,
):

    error_message = "Maximum bytes per object exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.bucket_test_max_bytes_per_item"] = "55"
        return settings


class QuotaCollectionMixin:
    def test_507_is_raised_if_quota_exceeded_on_record_creation(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": 42}}
        resp = self.app.post_json(
            "{}/records".format(self.collection_uri), body, headers=self.headers, status=507
        )

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            QUOTA_RESOURCE_NAME, self.collection_uri, COLLECTION_QUOTA_OBJECT_ID
        )
        self.assertStatsEqual(data, {"record_count": 1, "storage_size": storage_size})


class QuotaCollectionUpdateMixin:
    def test_507_is_raised_if_quota_exceeded_on_record_update(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        body = {"data": {"foo": 42, "bar": "This is a very long string."}}
        resp = self.app.patch_json(self.record_uri, body, headers=self.headers, status=507)

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        storage_size += record_size(self.record)

        self.assertFormattedError(
            resp, 507, ERRORS.FORBIDDEN, "Insufficient Storage", self.error_message
        )

        data = self.storage.get(
            QUOTA_RESOURCE_NAME, self.collection_uri, COLLECTION_QUOTA_OBJECT_ID
        )
        self.assertStatsEqual(data, {"record_count": 1, "storage_size": storage_size})

    def test_507_is_not_raised_if_quota_exceeded_on_record_delete(self):
        self.create_bucket()
        self.create_collection()
        self.create_record()
        self.app.delete(self.record_uri, headers=self.headers)

        # Check that the storage was not updated.
        storage_size = record_size(self.collection)
        data = self.storage.get(
            QUOTA_RESOURCE_NAME, self.collection_uri, COLLECTION_QUOTA_OBJECT_ID
        )
        self.assertStatsEqual(data, {"record_count": 0, "storage_size": storage_size})


class QuotaMaxBytesExceededCollectionSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin, QuotaWebTest
):

    error_message = "Collection maximum size exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_max_bytes"] = "100"
        return settings


class QuotaMaxBytesExceededCollectionBucketSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin, QuotaWebTest
):

    error_message = "Collection maximum size exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_test_max_bytes"] = "100"
        return settings


class QuotaMaxBytesExceededBucketCollectionSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin, QuotaWebTest
):

    error_message = "Collection maximum size exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_test_col_max_bytes"] = "100"
        return settings


class QuotaMaxItemsExceededCollectionSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest
):

    error_message = "Collection maximum number of objects exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_max_items"] = "1"
        return settings


class QuotaMaxItemsExceededCollectionBucketSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest
):

    error_message = "Collection maximum number of objects exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_test_max_items"] = "1"
        return settings


class QuotaMaxItemsExceededBucketCollectionSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest
):

    error_message = "Collection maximum number of objects exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_test_col_max_items"] = "1"
        return settings


class QuotaMaxBytesPerItemExceededCollectionSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaWebTest
):

    error_message = "Maximum bytes per object exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_max_bytes_per_item"] = "80"
        return settings


class QuotaMaxBytesPerItemExceededCollectionBucketSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin, QuotaWebTest
):

    error_message = "Maximum bytes per object exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_test_max_bytes_per_item"] = "80"
        return settings


class QuotaMaxBytesPerItemExceededBucketCollectionSettingsListenerTest(
    FormattedErrorMixin, QuotaCollectionMixin, QuotaCollectionUpdateMixin, QuotaWebTest
):

    error_message = "Maximum bytes per object exceeded "

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["quotas.collection_test_col_max_bytes_per_item"] = "80"
        return settings


class QuotasScriptsTest(unittest.TestCase):
    OLDEST_FIRST = Sort("last_modified", 1)
    BATCH_SIZE = 25

    def setUp(self):
        self.storage = mock.Mock()

    def test_rebuild_quotas_updates_records(self):
        paginated_data = [
            # get buckets
            iter([{"id": "bucket-1", "last_modified": 10}]),
            # get collections for first bucket
            iter(
                [
                    {"id": "collection-1", "last_modified": 100},
                    {"id": "collection-2", "last_modified": 200},
                ]
            ),
            # get records for first collection
            iter([{"id": "record-1", "last_modified": 110}]),
            # get records for second collection
            iter([{"id": "record-1b", "last_modified": 210}]),
        ]

        def paginated_mock(*args, **kwargs):
            return paginated_data.pop(0)

        with mock.patch("kinto.plugins.quotas.scripts.logger") as mocked_logger:
            with mock.patch(
                "kinto.plugins.quotas.scripts.paginated", side_effect=paginated_mock
            ) as mocked_paginated:
                scripts.rebuild_quotas(self.storage)

        mocked_paginated.assert_any_call(
            self.storage, resource_name="bucket", parent_id="", sorting=[self.OLDEST_FIRST]
        )
        mocked_paginated.assert_any_call(
            self.storage,
            resource_name="collection",
            parent_id="/buckets/bucket-1",
            sorting=[self.OLDEST_FIRST],
        )
        mocked_paginated.assert_any_call(
            self.storage,
            resource_name="record",
            parent_id="/buckets/bucket-1/collections/collection-1",
            sorting=[self.OLDEST_FIRST],
        )
        mocked_paginated.assert_any_call(
            self.storage,
            resource_name="record",
            parent_id="/buckets/bucket-1/collections/collection-2",
            sorting=[self.OLDEST_FIRST],
        )

        self.storage.update.assert_any_call(
            resource_name="quota",
            parent_id="/buckets/bucket-1",
            object_id="bucket_info",
            obj={"record_count": 2, "storage_size": 193, "collection_count": 2},
        )
        self.storage.update.assert_any_call(
            resource_name="quota",
            parent_id="/buckets/bucket-1/collections/collection-1",
            object_id="collection_info",
            obj={"record_count": 1, "storage_size": 78},
        )
        self.storage.update.assert_any_call(
            resource_name="quota",
            parent_id="/buckets/bucket-1/collections/collection-2",
            object_id="collection_info",
            obj={"record_count": 1, "storage_size": 79},
        )

        mocked_logger.info.assert_any_call(
            "Bucket bucket-1, collection collection-1. " "Final size: 1 records, 78 bytes."
        )
        mocked_logger.info.assert_any_call(
            "Bucket bucket-1, collection collection-2. " "Final size: 1 records, 79 bytes."
        )
        mocked_logger.info.assert_any_call(
            "Bucket bucket-1. Final size: " "2 collections, 2 records, 193 bytes."
        )

    def test_rebuild_quotas_doesnt_update_if_dry_run(self):
        paginated_data = [
            # get buckets
            iter([{"id": "bucket-1", "last_modified": 10}]),
            # get collections for first bucket
            iter([{"id": "collection-1", "last_modified": 100}]),
            # get records for first collection
            iter([{"id": "record-1", "last_modified": 110}]),
        ]

        def paginated_mock(*args, **kwargs):
            return paginated_data.pop(0)

        with mock.patch("kinto.plugins.quotas.scripts.logger") as mocked:
            with mock.patch("kinto.plugins.quotas.scripts.paginated", side_effect=paginated_mock):
                scripts.rebuild_quotas(self.storage, dry_run=True)

        assert not self.storage.update.called

        mocked.info.assert_any_call(
            "Bucket bucket-1, collection collection-1. " "Final size: 1 records, 78 bytes."
        )
        mocked.info.assert_any_call(
            "Bucket bucket-1. Final size: 1 collections, " "1 records, 114 bytes."
        )
