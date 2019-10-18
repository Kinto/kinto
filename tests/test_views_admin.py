import unittest

from pyramid.config import Configurator

from kinto.core import events, utils
from kinto.core.storage import exceptions
from kinto.core.testing import get_user_headers
from kinto.views.admin import get_parent_uri

from .support import MINIMALIST_BUCKET, MINIMALIST_COLLECTION, MINIMALIST_RECORD, BaseWebTest


class DeleteUserDataTest(BaseWebTest, unittest.TestCase):
    """Create some data belonging to a user, then delete the user.

    This user (and all their data) should be deleted. Thus, this user
    (and their data) is "doomed".

    To make sure we don't delete too much data, create some data owned
    by a different user which won't be deleted. This user (and their
    data) will be "safe". We'll use the normal self.headers user (see
    tests.support.BaseWebTest and kinto.core.get_user_headers) for
    this.

    We also want to ensure that the "doomed" user is removed correctly
    from "surviving" permissions and groups, so add the "doomed" user
    to some stuff belonging to the "safe" user too.

    """

    doomed_bucket_url = "/buckets/user_to_delete"
    doomed_collection_url = doomed_bucket_url + "/collections/collection_to_delete"
    doomed_bucket_collection_url = doomed_bucket_url + "/collections/collection"
    safe_bucket_url = "/buckets/user_safe"
    safe_bucket_doomed_collection_url = safe_bucket_url + "/collections/collection_to_delete"
    safe_collection_url = safe_bucket_url + "/collections/collection_safe"
    safe_collection_doomed_record_url = safe_collection_url + "/records/record_to_delete"
    safe_record_url = safe_collection_url + "/records/record_safe"
    safe_group_containing_doomed_user = safe_bucket_url + "/groups/silly-group"
    shared_bucket_url = "/buckets/both"
    doomed_user = get_user_headers("doomed", "trustno1")
    hmac_secret = "secret_hmac_for_userids"
    user_hash = utils.hmac_digest(hmac_secret, "mat:secret")
    user_principal = f"basicauth:{user_hash}"
    doomed_hash = utils.hmac_digest(hmac_secret, "doomed:trustno1")
    doomed_user_principal = f"basicauth:{doomed_hash}"
    delete_user_url = f"/__user_data__/{doomed_user_principal}"
    events = []

    @classmethod
    def listener(cls, event):
        cls.events.append(event)

    @classmethod
    def get_app_settings(cls, extras=None):
        dct = super().get_app_settings(extras=extras)
        dct["userid_hmac_secret"] = cls.hmac_secret
        dct["user-data_delete_principals"] = cls.user_principal
        dct["bucket_create_principals"] = "system.Authenticated"
        return dct

    @classmethod
    def make_app(cls, settings=None, config=None):
        settings = cls.get_app_settings(settings)
        config = Configurator(settings=settings)
        config.add_subscriber(cls.listener, events.ResourceChanged)
        config.commit()
        return super().make_app(settings=settings, config=config)

    def setUp(self):
        del self.events[:]
        super().setUp()
        self.app.put_json(self.doomed_bucket_url, MINIMALIST_BUCKET, headers=self.doomed_user)
        self.app.put_json(
            self.doomed_collection_url, MINIMALIST_COLLECTION, headers=self.doomed_user
        )
        # Temporarily grant write to self.user_principal to allow them
        # to create a collection
        self.app.patch_json(
            self.doomed_bucket_url,
            {"permissions": {"write": [self.user_principal]}},
            headers=self.doomed_user,
        )
        self.app.put_json(
            self.doomed_bucket_collection_url, MINIMALIST_COLLECTION, headers=self.headers
        )
        self.app.patch_json(
            self.doomed_bucket_url, {"permissions": {"write": []}}, headers=self.doomed_user
        )
        self.app.put_json(
            self.safe_bucket_url,
            {**MINIMALIST_BUCKET, "permissions": {"write": [self.doomed_user_principal]}},
            headers=self.headers,
        )
        self.app.put_json(
            self.safe_bucket_doomed_collection_url, MINIMALIST_COLLECTION, headers=self.doomed_user
        )
        self.app.put_json(self.safe_collection_url, MINIMALIST_COLLECTION, headers=self.headers)
        self.app.patch_json(
            self.safe_collection_url,
            {"permissions": {"write": [self.doomed_user_principal]}},
            headers=self.headers,
        )
        self.app.put_json(
            self.safe_collection_doomed_record_url, MINIMALIST_RECORD, headers=self.doomed_user
        )
        self.app.patch_json(
            self.safe_collection_url, {"permissions": {"write": []}}, headers=self.headers
        )
        # This record will automatically have "write" permission for
        # the safe user.
        self.app.put_json(
            self.safe_record_url,
            {**MINIMALIST_RECORD, "permissions": {"read": [self.doomed_user_principal]}},
            headers=self.headers,
        )
        self.app.put_json(
            self.shared_bucket_url,
            {
                **MINIMALIST_BUCKET,
                "permissions": {"write": [self.doomed_user_principal, self.user_principal]},
            },
            headers=self.doomed_user,
        )
        self.app.put_json(
            self.safe_group_containing_doomed_user,
            {"data": {"members": [self.doomed_user_principal, self.user_principal]}},
            headers=self.headers,
        )

        # Actually do the delete. Each `test_` method checks some
        # consequence of what got deleted.
        self.app.delete(self.delete_user_url, headers=self.headers)

    def test_other_methods_are_not_allowed(self):
        for url in ("/__user_data__", self.delete_user_url):
            self.app.head(url, headers=self.headers, status=405)
            self.app.get(url, headers=self.headers, status=405)
            self.app.put(url, headers=self.headers, status=405)
            self.app.patch(url, headers=self.headers, status=405)

    def test_doomed_bucket_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get(resource_name="bucket", parent_id="", object_id="user_to_delete")

    def test_doomed_bucket_collection_was_deleted(self):
        # Everything under this bucket should be gone
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get(
                resource_name="collection",
                parent_id=self.doomed_bucket_url,
                object_id="collection",
            )

    def test_doomed_bucket_doomed_collection_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get(
                resource_name="collection",
                parent_id=self.doomed_bucket_url,
                object_id="collection_to_delete",
            )

    def test_safe_bucket_was_not_deleted(self):
        self.storage.get(resource_name="bucket", parent_id="", object_id="user_safe")

    def test_safe_bucket_doomed_collection_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get(
                resource_name="collection",
                parent_id=self.safe_bucket_url,
                object_id="collection_to_delete",
            )

    def test_safe_collection_was_not_deleted(self):
        self.storage.get(
            resource_name="collection", parent_id=self.safe_bucket_url, object_id="collection_safe"
        )

    def test_safe_collection_safe_record_was_not_deleted(self):
        self.storage.get(
            resource_name="record", parent_id=self.safe_collection_url, object_id="record_safe"
        )

    def test_safe_collection_doomed_record_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get(
                resource_name="record",
                parent_id=self.safe_collection_url,
                object_id="record_to_delete",
            )

    def test_safe_group_not_deleted(self):
        principals = self.permission.get_user_principals(self.user_principal)
        self.assertEqual(principals, {"/buckets/user_safe/groups/silly-group"})

    def test_safe_group_doomed_user_was_removed(self):
        principals = self.permission.get_user_principals(self.doomed_user_principal)
        self.assertEqual(principals, set())

    def test_doomed_collection_no_longer_has_any_perms(self):
        permissions = self.permission.get_object_permissions(self.doomed_collection_url)
        self.assertEqual(permissions, {})

    def test_doomed_bucket_collection_no_longer_has_any_perms(self):
        permissions = self.permission.get_object_permissions(self.doomed_bucket_collection_url)
        self.assertEqual(permissions, {})

    def test_safe_bucket_no_longer_has_doomed_user_perm(self):
        permissions = self.permission.get_object_permissions(self.safe_bucket_url)
        self.assertEqual(permissions, {"write": {self.user_principal}})

    def test_safe_record_no_longer_has_doomed_user_perm(self):
        permissions = self.permission.get_object_permissions(self.safe_record_url)
        self.assertEqual(permissions, {"write": {self.user_principal}})

    def test_shared_bucket_was_not_deleted(self):
        self.storage.get(resource_name="bucket", parent_id="", object_id="both")

    def test_shared_bucket_permissions_are_correct(self):
        permissions = self.permission.get_object_permissions(self.shared_bucket_url)
        self.assertEqual(permissions, {"write": {self.user_principal}})

    def test_double_delete_is_ok(self):
        self.app.delete(self.delete_user_url, headers=self.headers)

    def test_cannot_delete_user_without_permission(self):
        # Only the user with self.headers can access this URL.
        self.app.delete(self.delete_user_url, headers=self.doomed_user, status=403)

    def test_event_emitted_for_bucket_deletion(self):
        delete_events = [
            e for e in self.events if e.payload["action"] == events.ACTIONS.DELETE.value
        ]
        bucket_events = [e for e in delete_events if e.payload["resource_name"] == "bucket"]
        # There should only be one such event, because all buckets
        # share a parent
        self.assertEqual(len(bucket_events), 1)
        # There should only be one such bucket
        self.assertEqual(len(bucket_events[0].impacted_objects), 1)
        event = bucket_events[0].impacted_objects[0]
        self.assertEqual(event["old"]["id"], "user_to_delete")

    def test_event_not_emitted_for_coalesced_collection_deletion(self):
        # Verify that collection deletion for
        # /buckets/user_to_delete/collections/collection_to_delete
        # was folded into bucket deletion for
        # /buckets/user_to_delete
        delete_events = [
            e for e in self.events if e.payload["action"] == events.ACTIONS.DELETE.value
        ]
        collection_events = [
            e for e in delete_events if e.payload["resource_name"] == "collection"
        ]
        # There should only be one such event, for /buckets/user_safe
        self.assertEqual(len(collection_events), 1)
        self.assertEqual(collection_events[0].payload["bucket_id"], "user_safe")
        # Nothing for user_to_delete, so it must have been coalesced

    def test_event_emitted_for_record_deletion(self):
        delete_events = [
            e for e in self.events if e.payload["action"] == events.ACTIONS.DELETE.value
        ]
        record_events = [e for e in delete_events if e.payload["resource_name"] == "record"]
        # Just one, for safe_collection_doomed_record_url
        self.assertEqual(len(record_events), 1)
        event = record_events[0]
        self.assertEqual(event.payload["bucket_id"], "user_safe")
        self.assertEqual(event.payload["collection_id"], "collection_safe")
        # Just the doomed record, not the safe one
        self.assertEqual(len(event.impacted_objects), 1)
        self.assertEqual(event.impacted_objects[0]["old"]["id"], "record_to_delete")


class GetParentUriTest(unittest.TestCase):
    def test_parent_uri_behaves_sensibly_for_unknown_resources(self):
        unknown_url = "/cities/prague/monuments/castle/foods/mushrooms"
        self.assertEqual(get_parent_uri(unknown_url), "/cities/prague/monuments/castle")

    def test_parent_uri_accepts_pathological_urls(self):
        # This shouldn't ever actually happen, and if it does happen
        # it's probably a sign of a larger incompatibility of this
        # method with the URL scheme
        self.assertEqual(get_parent_uri("/prague"), "")
