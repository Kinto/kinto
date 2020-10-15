import json
import re
import unittest
from unittest import mock

from pyramid import testing

from kinto import main as kinto_main
from kinto.core.testing import get_user_headers, skip_if_no_statsd

from .. import support

DATETIME_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}$"


class PluginSetup(unittest.TestCase):
    @skip_if_no_statsd
    def test_a_statsd_timer_is_used_for_history_if_configured(self):
        settings = {
            "statsd_url": "udp://127.0.0.1:8125",
            "includes": "kinto.plugins.history",
        }
        config = testing.setUp(settings=settings)
        with mock.patch("kinto.core.statsd.Client.timer") as mocked:
            kinto_main(None, config=config)
            mocked.assert_called_with("plugins.history")


class HistoryWebTest(support.BaseWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.history"
        return settings


class HelloViewTest(HistoryWebTest):
    def test_history_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("history", capabilities)


class HistoryViewTest(HistoryWebTest):
    def setUp(self):
        self.bucket_uri = "/buckets/test"
        self.app.put(self.bucket_uri, headers=self.headers)

        self.collection_uri = self.bucket_uri + "/collections/col"
        resp = self.app.put(self.collection_uri, headers=self.headers)
        self.collection = resp.json["data"]

        self.group_uri = self.bucket_uri + "/groups/grp"
        body = {"data": {"members": ["elle"]}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        self.group = resp.json["data"]

        self.record_uri = "/buckets/test/collections/col/records/rec"
        body = {"data": {"foo": 42}}
        resp = self.app.put_json(self.record_uri, body, headers=self.headers)
        self.record = resp.json["data"]

        self.history_uri = "/buckets/test/history"

    def test_only_get_and_delete_on_collection_are_allowed(self):
        self.app.put(self.history_uri, headers=self.headers, status=405)
        self.app.patch(self.history_uri, headers=self.headers, status=405)

    def test_only_collection_endpoint_is_available(self):
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        url = "{}/{}".format(self.bucket_uri, entry["id"])
        self.app.get(url, headers=self.headers, status=404)
        self.app.put(url, headers=self.headers, status=404)
        self.app.patch(url, headers=self.headers, status=404)
        self.app.delete(url, headers=self.headers, status=404)

    def test_tracks_user_and_date(self):
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][-1]
        assert entry["user_id"] == self.principal
        assert re.match(DATETIME_REGEX, entry["date"])

    #
    # Bucket
    #

    def test_history_contains_bucket_creation(self):
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][-1]
        assert entry["resource_name"] == "bucket"
        assert entry["bucket_id"] == "test"
        assert entry["action"] == "create"
        assert entry["uri"] == "/buckets/test"

    def test_history_supports_creation_via_plural_endpoint(self):
        resp = self.app.post_json("/buckets", {"data": {"id": "posted"}}, headers=self.headers)
        resp = self.app.get("/buckets/posted/history", headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["resource_name"] == "bucket"
        assert entry["bucket_id"] == "posted"
        assert entry["action"] == "create"
        assert entry["uri"] == "/buckets/posted"

    def test_tracks_bucket_attributes_update(self):
        body = {"data": {"foo": "baz"}}
        self.app.patch_json(self.bucket_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["data"]["foo"] == "baz"

    def test_tracks_bucket_permissions_update(self):
        body = {"permissions": {"read": ["admins"]}}
        self.app.patch_json(self.bucket_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["permissions"]["read"] == ["admins"]

    def test_bucket_delete_destroys_its_history_entries(self):
        self.app.delete(self.bucket_uri, headers=self.headers)
        storage = self.app.app.registry.storage
        stored_in_backend = storage.list_all(parent_id="/buckets/test", resource_name="history")
        assert len(stored_in_backend) == 0

    def test_delete_all_buckets_destroys_history_entries(self):
        self.app.put_json("/buckets/1", {"data": {"a": 1}}, headers=self.headers)

        self.app.delete("/buckets?a=1", headers=self.headers)

        # Entries about deleted bucket are gone.
        storage = self.app.app.registry.storage
        stored_in_backend = storage.list_all(parent_id="/buckets/1", resource_name="history")
        assert len(stored_in_backend) == 0

        # Entries of other buckets are still here.
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][-1]
        assert entry["bucket_id"] == "test"
        assert entry["action"] == "create"

    #
    # Collection
    #

    def test_tracks_collection_creation(self):
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][2]
        cid = self.collection["id"]
        assert entry["resource_name"] == "collection"
        assert "bucket_id" not in entry
        assert entry["collection_id"] == cid
        assert entry["action"] == "create"
        assert entry["uri"] == "/buckets/test/collections/{}".format(cid)

    def test_tracks_collection_attributes_update(self):
        body = {"data": {"foo": "baz"}}
        self.app.patch_json(self.collection_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["data"]["foo"] == "baz"

    def test_tracks_collection_permissions_update(self):
        body = {"permissions": {"read": ["admins"]}}
        self.app.patch_json(self.collection_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["permissions"]["read"] == ["admins"]

    def test_tracks_collection_delete(self):
        self.app.delete(self.collection_uri, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "delete"
        assert entry["target"]["data"]["deleted"] is True

    def test_tracks_multiple_collections_delete(self):
        self.app.put(self.bucket_uri + "/collections/col2", headers=self.headers)

        self.app.delete(self.bucket_uri + "/collections", headers=self.headers)

        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "delete"
        assert entry["target"]["data"]["id"] in (self.collection["id"], "col2")

    #
    # Group
    #

    def test_tracks_group_creation(self):
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][1]
        assert entry["resource_name"] == "group"
        assert "bucket_id" not in entry
        assert entry["group_id"] == self.group["id"]
        assert entry["action"] == "create"
        assert entry["uri"] == "/buckets/test/groups/{}".format(self.group["id"])

    def test_tracks_group_attributes_update(self):
        body = {"data": {"foo": "baz", "members": ["lui"]}}
        self.app.patch_json(self.group_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["data"]["foo"] == "baz"
        assert entry["target"]["data"]["members"] == ["lui"]

    def test_tracks_group_permissions_update(self):
        body = {"permissions": {"read": ["admins"]}}
        self.app.patch_json(self.group_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["permissions"]["read"] == ["admins"]

    def test_tracks_group_delete(self):
        self.app.delete(self.group_uri, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "delete"
        assert entry["target"]["data"]["deleted"] is True

    def test_tracks_multiple_groups_delete(self):
        self.app.put_json(
            self.bucket_uri + "/groups/g2", {"data": {"members": ["her"]}}, headers=self.headers
        )

        self.app.delete(self.bucket_uri + "/groups", headers=self.headers)

        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "delete"
        assert entry["target"]["data"]["id"] in (self.group["id"], "g2")

    #
    # Record
    #

    def test_tracks_record_creation(self):
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        cid = self.collection["id"]
        rid = self.record["id"]
        assert entry["resource_name"] == "record"
        assert "bucket_id" not in entry
        assert entry["collection_id"] == cid
        assert entry["record_id"] == rid
        assert entry["action"] == "create"
        assert entry["uri"] == "/buckets/test/collections/{}/records/{}".format(cid, rid)
        assert entry["target"]["data"]["foo"] == 42
        assert entry["target"]["permissions"]["write"][0].startswith("basicauth:")

    def test_tracks_record_attributes_update(self):
        resp = self.app.patch_json(self.record_uri, {"data": {"foo": "baz"}}, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["data"]["foo"] == "baz"

    def test_tracks_record_permissions_update(self):
        body = {"permissions": {"read": ["admins"]}}
        resp = self.app.patch_json(self.record_uri, body, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "update"
        assert entry["target"]["permissions"]["read"] == ["admins"]

    def test_tracks_record_delete(self):
        resp = self.app.delete(self.record_uri, headers=self.headers)
        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "delete"
        assert entry["target"]["data"]["deleted"] is True

    def test_tracks_multiple_records_delete(self):
        records_uri = self.collection_uri + "/records"
        body = {"data": {"foo": 43}}
        resp = self.app.post_json(records_uri, body, headers=self.headers)
        rid = resp.json["data"]["id"]

        self.app.delete(records_uri, headers=self.headers)

        resp = self.app.get(self.history_uri, headers=self.headers)
        entry = resp.json["data"][0]
        assert entry["action"] == "delete"
        assert entry["target"]["data"]["id"] in (self.record["id"], rid)

    def test_does_not_track_records_during_massive_deletion(self):
        body = {"data": {"pim": "pam"}}
        records_uri = self.collection_uri + "/records"
        self.app.post_json(records_uri, body, headers=self.headers)

        self.app.delete(self.collection_uri, headers=self.headers)

        resp = self.app.get(self.history_uri, headers=self.headers)
        deletion_entries = [e for e in resp.json["data"] if e["action"] == "delete"]
        assert len(deletion_entries) == 1


class HistoryDeletionTest(HistoryWebTest):
    def setUp(self):
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)
        body = {"data": {"foo": 42}}
        self.app.put_json("/buckets/bid/collections/cid/records/rid", body, headers=self.headers)

    def test_full_deletion(self):
        self.app.delete("/buckets/bid/history", headers=self.headers)
        resp = self.app.get("/buckets/bid/history", headers=self.headers)
        assert len(resp.json["data"]) == 0

    def test_partial_deletion(self):
        resp = self.app.get("/buckets/bid/history", headers=self.headers)
        before = int(json.loads(resp.headers["ETag"]))
        self.app.put("/buckets/bid/collections/cid2", headers=self.headers)

        # Delete everything before the last entry (exclusive)
        self.app.delete("/buckets/bid/history?_before={}".format(before), headers=self.headers)

        resp = self.app.get("/buckets/bid/history", headers=self.headers)
        assert len(resp.json["data"]) == 2  # record + new collection


class FilteringTest(HistoryWebTest):
    def setUp(self):
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/0", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)
        self.app.put("/buckets/0/collections/1", headers=self.headers)
        body = {"data": {"foo": 42}}
        self.app.put_json("/buckets/bid/collections/cid/records/rid", body, headers=self.headers)
        body = {"data": {"foo": 0}}
        self.app.put_json("/buckets/0/collections/1/records/2", body, headers=self.headers)
        body = {"data": {"foo": "bar"}}
        self.app.patch_json("/buckets/bid/collections/cid/records/rid", body, headers=self.headers)
        self.app.delete("/buckets/bid/collections/cid/records/rid", headers=self.headers)

    def test_filter_by_unknown_field_is_not_allowed(self):
        self.app.get("/buckets/bid/history?movie=bourne", headers=self.headers, status=400)

    def test_filter_by_action(self):
        resp = self.app.get("/buckets/bid/history?action=delete", headers=self.headers)
        assert len(resp.json["data"]) == 1

    def test_filter_by_resource(self):
        resp = self.app.get("/buckets/bid/history?resource_name=bucket", headers=self.headers)
        assert len(resp.json["data"]) == 1

    def test_filter_by_uri(self):
        uri = "/buckets/bid/collections/cid/records/rid"
        resp = self.app.get("/buckets/bid/history?uri={}".format(uri), headers=self.headers)
        assert len(resp.json["data"]) == 3  # create / update / delete

    def test_allows_diff_between_two_versions_of_a_record(self):
        uri = "/buckets/bid/collections/cid/records/rid"
        querystring = "?uri={}&_limit=2&_sort=last_modified".format(uri)
        resp = self.app.get("/buckets/bid/history{}".format(querystring), headers=self.headers)
        entries = resp.json["data"]
        version1 = entries[0]["target"]["data"]
        version2 = entries[1]["target"]["data"]
        diff = [
            (k, version1[k], version2[k])
            for k in version1.keys()
            if k != "last_modified" and version2[k] != version1[k]
        ]
        assert diff == [("foo", 42, "bar")]

    def test_filter_by_bucket(self):
        uri = "/buckets/bid/history?bucket_id=bid"
        resp = self.app.get(uri, headers=self.headers)
        # This is equivalent to filtering by resource_name=bucket,
        # since only entries for bucket have ``bucket_id`` attribute.
        assert len(resp.json["data"]) == 1

    def test_filter_by_collection(self):
        uri = "/buckets/bid/history?collection_id=cid"
        resp = self.app.get(uri, headers=self.headers)
        assert len(resp.json["data"]) == 4

    def test_filter_by_numeric_bucket(self):
        uri = "/buckets/0/history?bucket_id=0"
        resp = self.app.get(uri, headers=self.headers)
        assert len(resp.json["data"]) == 1

    def test_filter_by_numeric_collection(self):
        uri = "/buckets/0/history?collection_id=1"
        resp = self.app.get(uri, headers=self.headers)
        assert len(resp.json["data"]) == 2

    def test_filter_by_numeric_record(self):
        uri = "/buckets/0/history?record_id=2"
        resp = self.app.get(uri, headers=self.headers)
        assert len(resp.json["data"]) == 1

    def test_filter_by_target_fields(self):
        uri = "/buckets/bid/history?target.data.id=rid"
        resp = self.app.get(uri, headers=self.headers)
        assert len(resp.json["data"]) == 3  # create, update, delete

    def test_limit_results(self):
        resp = self.app.get("/buckets/bid/history?_limit=2", headers=self.headers)
        assert len(resp.json["data"]) == 2
        assert "Next-Page" in resp.headers

    def test_filter_returned_fields(self):
        resp = self.app.get("/buckets/bid/history?_fields=uri,action", headers=self.headers)
        assert sorted(resp.json["data"][0].keys()) == ["action", "id", "last_modified", "uri"]

    def test_sort_by_date(self):
        resp = self.app.get("/buckets/bid/history?_sort=date", headers=self.headers)
        entries = resp.json["data"]
        assert entries[0]["date"] < entries[-1]["date"]


class BulkTest(HistoryWebTest):
    def setUp(self):
        body = {
            "defaults": {"method": "POST", "path": "/buckets/bid/collections/cid/records"},
            "requests": [
                {"path": "/buckets/bid", "method": "PUT"},
                {"path": "/buckets/bid/collections", "body": {"data": {"id": "cid"}}},
                {"body": {"data": {"id": "a", "attr": 1}}},
                {"body": {"data": {"id": "b", "attr": 2}}},
                {"body": {"data": {"id": "c", "attr": 3}}},
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)

    def test_post_on_collection(self):
        resp = self.app.get("/buckets/bid/history", headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) == 5
        assert entries[0]["uri"] == "/buckets/bid/collections/cid/records/c"
        assert entries[-2]["uri"] == "/buckets/bid/collections/cid"

    def test_delete_on_collection(self):
        body = {
            "defaults": {"method": "DELETE"},
            "requests": [
                {"path": "/buckets/bid/collections/cid/records/a"},
                {"path": "/buckets/bid/collections/cid/records/b"},
                {"path": "/buckets/bid/collections/cid/records/c"},
            ],
        }
        self.app.post_json("/batch", body, headers=self.headers)
        resp = self.app.get("/buckets/bid/history", headers=self.headers)
        entries = resp.json["data"]
        assert entries[0]["uri"] == "/buckets/bid/collections/cid/records/c"
        assert entries[1]["uri"] == "/buckets/bid/collections/cid/records/b"
        assert entries[2]["uri"] == "/buckets/bid/collections/cid/records/a"

    def test_multiple_patch(self):
        # Kinto/kinto#942
        requests = [
            {
                "method": "PATCH",
                "path": "/buckets/bid/collections/cid/records/{}".format(label),
                "body": {"data": {"label": label}},
            }
            for label in ("a", "b", "c")
        ]
        self.app.post_json("/batch", {"requests": requests}, headers=self.headers)
        resp = self.app.get("/buckets/bid/history", headers=self.headers)
        entries = resp.json["data"]
        for entry in entries:
            if entry["resource_name"] != "record":
                continue
            assert entry["record_id"] == entry["target"]["data"]["id"]


class DefaultBucketTest(HistoryWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.default_bucket " "kinto.plugins.history"
        return settings

    def setUp(self):
        resp = self.app.get("/", headers=self.headers)
        self.bucket_id = resp.json["user"]["bucket"]
        self.history_uri = "/buckets/{}/history".format(self.bucket_id)

    def test_history_can_be_accessed_via_default_alias(self):
        self.app.get("/buckets/default/collections/blah", headers=self.headers)
        resp = self.app.get("/buckets/default/history", headers=self.headers)
        assert len(resp.json["data"]) == 2

    def test_implicit_creations_are_listed(self):
        body = {"data": {"foo": 42}}
        resp = self.app.post_json(
            "/buckets/default/collections/blah/records", body, headers=self.headers
        )
        record = resp.json["data"]

        resp = self.app.get(self.history_uri, headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) == 3

        bucket_uri = "/buckets/{}".format(self.bucket_id)
        assert entries[2]["resource_name"] == "bucket"
        assert entries[2]["bucket_id"] == self.bucket_id
        assert entries[2]["uri"] == bucket_uri
        assert entries[2]["target"]["permissions"]["write"][0] == self.principal

        collection_uri = bucket_uri + "/collections/blah"
        assert entries[1]["resource_name"] == "collection"
        assert "bucket_id" not in entries[1]
        assert entries[1]["collection_id"] == "blah"
        assert entries[1]["uri"] == collection_uri
        assert entries[1]["target"]["permissions"]["write"][0] == self.principal

        record_uri = collection_uri + "/records/{}".format(record["id"])
        assert entries[0]["resource_name"] == "record"
        assert "bucket_id" not in entries[1]
        assert entries[0]["collection_id"] == "blah"
        assert entries[0]["record_id"] == record["id"]
        assert entries[0]["uri"] == record_uri
        assert entries[0]["target"]["data"]["foo"] == 42
        assert entries[0]["target"]["permissions"]["write"][0] == self.principal


class PermissionsTest(HistoryWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["experimental_permissions_endpoint"] = "true"
        return settings

    def setUp(self):
        self.alice_headers = get_user_headers("alice")
        self.bob_headers = get_user_headers("bob")
        self.julia_headers = get_user_headers("julia")

        self.alice_principal = (
            "basicauth:d5b0026601f1b251974e09548d44155e16" "812e3c64ff7ae053fe3542e2ca1570"
        )
        self.bob_principal = (
            "basicauth:c031ced27503f788b102ca54269a062ec737" "94bb075154c74a0d4311e74ca8b6"
        )
        self.julia_principal = (
            "basicauth:d8bab8d9fe0510fcaf9b5ad5942c027fc" "2fdf80b6dc59cc3c48d12a2fcb18f1c"
        )

        bucket = {"permissions": {"read": [self.alice_principal]}}
        collection = {"permissions": {"read": [self.julia_principal]}}
        record = {"permissions": {"write": [self.bob_principal, self.alice_principal]}}
        self.app.put("/buckets/author-only", headers=self.headers)
        self.app.put_json("/buckets/test", bucket, headers=self.headers)
        self.app.put_json(
            "/buckets/test/groups/admins", {"data": {"members": []}}, headers=self.headers
        )
        self.app.put_json(
            "/buckets/test/collections/alice-julia", collection, headers=self.headers
        )
        self.app.put_json("/buckets/test/collections/author-only", headers=self.headers)
        self.app.post_json(
            "/buckets/test/collections/alice-julia/records", record, headers=self.headers
        )
        self.app.post_json(
            "/buckets/test/collections/alice-julia/records",
            {"permissions": {"read": ["system.Authenticated"]}},
            headers=self.headers,
        )

    def test_author_can_read_everything(self):
        resp = self.app.get("/buckets/test/history", headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) == 6  # everything.

    def test_read_permission_can_be_given_to_anybody_via_settings(self):
        with mock.patch.dict(
            self.app.app.registry.settings, [("history_read_principals", "system.Everyone")]
        ):
            resp = self.app.get("/buckets/test/history", headers=get_user_headers("tartan:pion"))
            entries = resp.json["data"]
            assert len(entries) == 6  # everything.

    def test_bucket_read_allows_whole_history(self):
        resp = self.app.get("/buckets/test/history", headers=self.alice_headers)
        entries = resp.json["data"]
        assert len(entries) == 6  # everything.

        self.app.get("/buckets/author-only/history", headers=self.alice_headers, status=403)

    def test_collection_read_restricts_to_collection(self):
        resp = self.app.get("/buckets/test/history", headers=self.julia_headers)
        entries = resp.json["data"]
        assert len(entries) == 3
        assert entries[0]["resource_name"] == "record"
        assert entries[1]["resource_name"] == "record"
        assert entries[2]["resource_name"] == "collection"

    def test_write_on_record_restricts_to_record(self):
        resp = self.app.get("/buckets/test/history", headers=self.bob_headers)
        entries = resp.json["data"]
        assert len(entries) == 2
        assert "system.Authenticated" in entries[0]["target"]["permissions"]["read"]
        assert entries[0]["resource_name"] == "record"
        assert self.bob_principal in entries[1]["target"]["permissions"]["write"]
        assert entries[1]["resource_name"] == "record"

    def test_publicly_readable_record_allows_any_authenticated(self):
        resp = self.app.get("/buckets/test/history", headers=get_user_headers("jack:"))
        entries = resp.json["data"]
        assert len(entries) == 1
        assert "system.Authenticated" in entries[0]["target"]["permissions"]["read"]
        assert entries[0]["resource_name"] == "record"

    def test_new_entries_are_not_readable_if_permission_is_removed(self):
        resp = self.app.get("/buckets/test/history", headers=self.alice_headers)
        before = resp.headers["ETag"]

        # Remove alice from read permission.
        self.app.patch_json("/buckets/test", {"permissions": {"read": []}}, headers=self.headers)

        # Create new collection.
        self.app.put_json("/buckets/test/collections/new-one", headers=self.headers)

        # History did not evolve for alice.
        resp = self.app.get("/buckets/test/history", headers=self.alice_headers)
        assert resp.headers["ETag"] != before

    def test_history_entries_are_not_listed_in_permissions_endpoint(self):
        resp = self.app.get("/permissions", headers=self.headers)
        entries = [e["resource_name"] == "history" for e in resp.json["data"]]
        assert not any(entries)


class ExcludeResourcesTest(HistoryWebTest):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["history.exclude_resources"] = (
            "/buckets/a " "/buckets/b/collections/a " "/buckets/b/groups/a"
        )
        return settings

    def setUp(self):
        group = {"data": {"members": []}}
        self.app.put_json("/buckets/a", headers=self.headers)
        self.app.put_json("/buckets/a/groups/admins", group, headers=self.headers)
        self.app.put_json("/buckets/b", headers=self.headers)
        self.app.put_json("/buckets/b/groups/a", group, headers=self.headers)
        self.app.put_json("/buckets/b/collections/a", headers=self.headers)
        self.app.put_json("/buckets/b/collections/a/records/1", headers=self.headers)
        self.app.put_json("/buckets/b/collections/b", headers=self.headers)
        self.app.put_json("/buckets/b/collections/b/records/1", headers=self.headers)

    def test_whole_buckets_can_be_excluded(self):
        resp = self.app.get("/buckets/a/history", headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) == 0  # nothing.

    def test_some_specific_collection_can_be_excluded(self):
        resp = self.app.get("/buckets/b/history?collection_id=b", headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) > 0

        resp = self.app.get("/buckets/b/history?collection_id=a", headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) == 0  # nothing.

    def test_some_specific_object_can_be_excluded(self):
        resp = self.app.get("/buckets/b/history?group_id=a", headers=self.headers)
        entries = resp.json["data"]
        assert len(entries) == 0  # nothing.


class DisabledExplicitPermissionsTest(HistoryWebTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["explicit_permissions"] = "false"
        return settings

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_headers = {**cls.headers, **get_user_headers("alice")}
        cls.alice_principal = (
            "basicauth:d5b0026601f1b251974e09548d44155e16812e3c64ff7ae053fe3542e2ca1570"
        )

    def setUp(self):
        self.app.put_json(
            "/buckets/test",
            {"permissions": {"write": ["system.Authenticated"]}},
            headers=self.headers,
        )
        self.app.put_json(
            "/buckets/test/collections/test",
            {"permissions": {"write": ["system.Authenticated"]}},
            headers=self.headers,
        )

    def test_history_can_still_be_read(self):
        self.app.post_json("/buckets/test/collections/test/records", headers=self.alice_headers)

        resp = self.app.get("/buckets/test/history", headers=self.alice_headers)
        self.assertEqual(
            [(entry["action"], entry["resource_name"]) for entry in resp.json["data"]],
            [("create", "record"), ("create", "collection"), ("create", "bucket")],
        )
