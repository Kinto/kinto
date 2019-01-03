import unittest

from kinto.core.storage import exceptions
from kinto.core.testing import get_user_headers
from kinto.core import utils

from .support import (
    BaseWebTest,
    MINIMALIST_BUCKET,
    MINIMALIST_COLLECTION,
    MINIMALIST_RECORD,
)


class DeleteUserDataTest(BaseWebTest, unittest.TestCase):
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

    @classmethod
    def get_app_settings(cls, extras=None):
        dct = super().get_app_settings(extras=extras)
        dct["userid_hmac_secret"] = cls.hmac_secret
        dct["user-data_delete_principals"] = cls.user_principal
        dct["bucket_create_principals"] = "system.Authenticated"
        return dct

    def setUp(self):
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

    def test_doomed_bucket_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get("bucket", "", "user_to_delete")

    def test_doomed_bucket_collection_was_deleted(self):
        # Everything under this bucket should be gone
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get("collection", self.doomed_bucket_url, "collection")

    def test_doomed_bucket_doomed_collection_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get("collection", self.doomed_bucket_url, "collection_to_delete")

    def test_safe_bucket_was_not_deleted(self):
        self.storage.get("bucket", "", "user_safe")

    def test_safe_bucket_doomed_collection_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get("collection", self.safe_bucket_url, "collection_to_delete")

    def test_safe_collection_was_not_deleted(self):
        self.storage.get("collection", self.safe_bucket_url, "collection_safe")

    def test_safe_collection_safe_record_was_not_deleted(self):
        self.storage.get("record", self.safe_collection_url, "record_safe")

    def test_safe_collection_doomed_record_was_deleted(self):
        with self.assertRaises(exceptions.ObjectNotFoundError):
            self.storage.get("record", self.safe_collection_url, "record_to_delete")

    def test_safe_group_doomed_user_was_removed(self):
        principals = self.permission.get_user_principals(self.doomed_user_principal)
        for principal in principals:
            if principal.startswith("system:"):
                continue
            if principal == self.doomed_user_principal:
                continue
            self.fail(f"Got a leftover principal: {principal}")

    def test_doomed_collection_no_longer_has_any_perms(self):
        permissions = self.permission.get_object_permissions(self.doomed_collection_url)
        self.assertEqual(permissions, {})

    def test_doomed_bucket_collection_no_longer_has_any_perms(self):
        permissions = self.permission.get_object_permissions(self.doomed_bucket_collection_url)
        self.assertEqual(permissions, {})

    def test_safe_bucket_no_longer_has_doomed_user_perm(self):
        permissions = self.permission.get_object_permissions(self.safe_bucket_url)
        for perm, principals in permissions.items():
            self.assertNotIn(self.doomed_user_principal, principals)

    def test_safe_record_no_longer_has_doomed_user_perm(self):
        permissions = self.permission.get_object_permissions(self.safe_record_url)
        for perm, principals in permissions.items():
            self.assertNotIn(self.doomed_user_principal, principals)

    def test_shared_bucket_was_not_deleted(self):
        self.storage.get("bucket", "", "both")

    def test_shared_bucket_permissions_are_correct(self):
        permissions = self.permission.get_object_permissions(self.shared_bucket_url)
        self.assertEqual(permissions, {"write": {self.user_principal}})

    def test_double_delete_is_ok(self):
        self.app.delete(self.delete_user_url, headers=self.headers)

    def test_cannot_delete_user_without_permission(self):
        # Only the user with self.headers can access this URL.
        self.app.delete(self.delete_user_url, headers=self.doomed_user, status=403)
