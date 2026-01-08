import unittest
from types import SimpleNamespace
from unittest import mock

from kinto.core.permission.memory import Permission
from kinto.core.scripts import rename_collection
from kinto.core.storage.memory import Storage


class TestRenameCollection(unittest.TestCase):
    def setUp(self):
        self.registry = SimpleNamespace()
        self.registry.storage = Storage()
        self.registry.permission = Permission()
        self.env = {"registry": self.registry}

        # Create source bucket and collection
        self.registry.storage.create("bucket", "", {"id": "chefclub"})
        self.registry.storage.create("collection", "/buckets/chefclub", {"id": "recipes"})
        # Create a record
        self.registry.storage.create(
            "record", "/buckets/chefclub/collections/recipes", {"id": "r1", "data": "a"}
        )
        # Create dest bucket
        self.registry.storage.create("bucket", "", {"id": "chefclub-v2"})

        # Add permissions
        self.registry.permission.replace_object_permissions(
            "/buckets/chefclub/collections/recipes", {"read": {"group:chefs"}}
        )
        self.registry.permission.replace_object_permissions(
            "/buckets/chefclub/collections/recipes/records/r1", {"read": {"user:alice"}}
        )

    def test_rename_moves_collection_records_and_permissions(self):
        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes"
        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Collection exists at destination
        coll = self.registry.storage.get("collection", "/buckets/chefclub-v2", "recipes")
        self.assertEqual(coll["id"], "recipes")

        # Record moved
        rec = self.registry.storage.get("record", "/buckets/chefclub-v2/collections/recipes", "r1")
        self.assertEqual(rec["id"], "r1")
        self.assertEqual(rec["data"], "a")

        # Permissions moved
        perms_coll = self.registry.permission.get_objects_permissions(
            ["/buckets/chefclub-v2/collections/recipes"]
        )[0]
        self.assertIn("read", perms_coll)
        self.assertEqual(perms_coll["read"], {"group:chefs"})

        perms_rec = self.registry.permission.get_objects_permissions(
            ["/buckets/chefclub-v2/collections/recipes/records/r1"]
        )[0]
        self.assertIn("read", perms_rec)
        self.assertEqual(perms_rec["read"], {"user:alice"})

        # Source should no longer exist
        with self.assertRaises(Exception):
            self.registry.storage.get("collection", "/buckets/chefclub", "recipes")

        with self.assertRaises(Exception):
            self.registry.storage.get("record", "/buckets/chefclub/collections/recipes", "r1")

    def test_rename_preserves_tombstones(self):
        # Create another record and delete it so it becomes a tombstone.
        self.registry.storage.create(
            "record", "/buckets/chefclub/collections/recipes", {"id": "r2", "data": "b"}
        )
        self.registry.storage.delete("record", "/buckets/chefclub/collections/recipes", "r2")

        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes2"
        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Tombstone exists at destination
        tombstones = self.registry.storage.list_all(
            "record", "/buckets/chefclub-v2/collections/recipes2", include_deleted=True
        )
        # One of the returned items should have deleted flag True for r2
        self.assertTrue(any(t.get("deleted", False) for t in tombstones))

    def test_rename_force_overwrites_destination(self):
        # Create destination collection with a record that should be removed when force=True
        self.registry.storage.create("collection", "/buckets/chefclub-v2", {"id": "recipes"})
        self.registry.storage.create(
            "record", "/buckets/chefclub-v2/collections/recipes", {"id": "willbe", "data": "z"}
        )

        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes"
        res = rename_collection(self.env, src, dst, force=True)
        self.assertEqual(res, 0)

        # 'willbe' should be gone and replaced by 'r1'
        with self.assertRaises(Exception):
            self.registry.storage.get(
                "record", "/buckets/chefclub-v2/collections/recipes", "willbe"
            )
        rec = self.registry.storage.get("record", "/buckets/chefclub-v2/collections/recipes", "r1")
        self.assertEqual(rec["data"], "a")

    def test_rename_dry_run_does_not_modify(self):
        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes"
        res = rename_collection(self.env, src, dst, dry_run=True)
        self.assertEqual(res, 0)

        # Source should still exist and nothing was added to destination
        coll = self.registry.storage.get("collection", "/buckets/chefclub", "recipes")
        self.assertEqual(coll["id"], "recipes")
        with self.assertRaises(Exception):
            self.registry.storage.get("collection", "/buckets/chefclub-v2", "recipes")

    def test_rename_invalid_source_path(self):
        """Test error handling for invalid source collection path."""
        src = "invalid/path/format"
        dst = "/buckets/chefclub-v2/collections/recipes"
        with self.assertRaises(ValueError) as ctx:
            rename_collection(self.env, src, dst)
        self.assertIn("Invalid collection path", str(ctx.exception))

    def test_rename_invalid_destination_path(self):
        """Test error handling for invalid destination collection path."""
        src = "/buckets/chefclub/collections/recipes"
        dst = "also/invalid"
        with self.assertRaises(ValueError) as ctx:
            rename_collection(self.env, src, dst)
        self.assertIn("Invalid collection path", str(ctx.exception))

    def test_rename_source_equals_destination(self):
        """Test error when source and destination are identical."""
        src = "/buckets/chefclub/collections/recipes"
        with self.assertRaises(ValueError) as ctx:
            rename_collection(self.env, src, src)
        self.assertIn("must be different", str(ctx.exception))

    def test_rename_nonexistent_source_collection(self):
        """Test error when source collection does not exist."""
        src = "/buckets/chefclub/collections/nonexistent"
        dst = "/buckets/chefclub-v2/collections/recipes"
        with self.assertRaises(Exception):
            rename_collection(self.env, src, dst)

    def test_rename_nonexistent_destination_bucket(self):
        """Test error when destination bucket does not exist."""
        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/nonexistent-bucket/collections/recipes"
        with self.assertRaises(Exception):
            rename_collection(self.env, src, dst)

    def test_rename_destination_exists_without_force(self):
        """Test error when destination collection exists and force is False."""
        # Create destination collection
        self.registry.storage.create("collection", "/buckets/chefclub-v2", {"id": "recipes"})

        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes"
        with self.assertRaises(ValueError) as ctx:
            rename_collection(self.env, src, dst, force=False)
        self.assertIn("exists", str(ctx.exception))

    def test_rename_without_permission_backend(self):
        """Test rename when no permission backend is available."""
        # Create a registry without permission backend
        registry = SimpleNamespace()
        registry.storage = Storage()
        env = {"registry": registry}

        registry.storage.create("bucket", "", {"id": "source"})
        registry.storage.create("collection", "/buckets/source", {"id": "coll"})
        registry.storage.create("bucket", "", {"id": "dest"})
        registry.storage.create(
            "record", "/buckets/source/collections/coll", {"id": "rec1", "data": "test"}
        )

        src = "/buckets/source/collections/coll"
        dst = "/buckets/dest/collections/coll"
        res = rename_collection(env, src, dst)
        self.assertEqual(res, 0)

        # Verify collection was moved
        coll = registry.storage.get("collection", "/buckets/dest", "coll")
        self.assertEqual(coll["id"], "coll")
        rec = registry.storage.get("record", "/buckets/dest/collections/coll", "rec1")
        self.assertEqual(rec["data"], "test")

    def test_rename_collection_without_permissions(self):
        """Test rename when collection/records have no permissions set."""
        # Clear permissions
        self.registry.permission.flush()

        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes"
        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Verify move succeeded
        coll = self.registry.storage.get("collection", "/buckets/chefclub-v2", "recipes")
        self.assertEqual(coll["id"], "recipes")

    def test_rename_collection_with_multiple_records(self):
        """Test rename with multiple records and permissions."""
        # Create additional records
        for i in range(2, 5):
            self.registry.storage.create(
                "record",
                "/buckets/chefclub/collections/recipes",
                {"id": f"r{i}", "data": f"item{i}"},
            )
            self.registry.permission.replace_object_permissions(
                f"/buckets/chefclub/collections/recipes/records/r{i}",
                {"write": {"user:bob"}},
            )

        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes3"
        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Verify all records moved
        for i in range(1, 5):
            rec = self.registry.storage.get(
                "record", "/buckets/chefclub-v2/collections/recipes3", f"r{i}"
            )
            self.assertIsNotNone(rec)
            # Verify permissions moved for records with permissions
            if i > 1:
                perms = self.registry.permission.get_objects_permissions(
                    [f"/buckets/chefclub-v2/collections/recipes3/records/r{i}"]
                )[0]
                self.assertIn("write", perms)

    def test_rename_empty_collection(self):
        """Test rename of a collection with no records."""
        # Create empty collection
        self.registry.storage.create("bucket", "", {"id": "empty-bucket"})
        self.registry.storage.create("collection", "/buckets/empty-bucket", {"id": "empty"})
        self.registry.permission.replace_object_permissions(
            "/buckets/empty-bucket/collections/empty", {"read": {"system.Everyone"}}
        )

        src = "/buckets/empty-bucket/collections/empty"
        dst = "/buckets/chefclub-v2/collections/empty"
        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Verify collection moved with its permissions
        coll = self.registry.storage.get("collection", "/buckets/chefclub-v2", "empty")
        self.assertEqual(coll["id"], "empty")
        perms = self.registry.permission.get_objects_permissions(
            ["/buckets/chefclub-v2/collections/empty"]
        )[0]
        self.assertIn("read", perms)

    def test_rename_force_with_permission_cleanup(self):
        """Test that force overwrite properly cleans up destination permissions."""
        # Create destination with permissions to be cleared
        self.registry.storage.create("collection", "/buckets/chefclub-v2", {"id": "recipes"})
        self.registry.storage.create(
            "record",
            "/buckets/chefclub-v2/collections/recipes",
            {"id": "old-rec", "data": "old"},
        )
        self.registry.permission.replace_object_permissions(
            "/buckets/chefclub-v2/collections/recipes", {"admin": {"user:admin"}}
        )
        self.registry.permission.replace_object_permissions(
            "/buckets/chefclub-v2/collections/recipes/records/old-rec", {"write": {"user:bob"}}
        )

        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes"
        res = rename_collection(self.env, src, dst, force=True)
        self.assertEqual(res, 0)

        # Old record should be gone
        with self.assertRaises(Exception):
            self.registry.storage.get(
                "record", "/buckets/chefclub-v2/collections/recipes", "old-rec"
            )

        # New record should be there
        rec = self.registry.storage.get("record", "/buckets/chefclub-v2/collections/recipes", "r1")
        self.assertEqual(rec["id"], "r1")

        # Old destination permissions should be overwritten with source permissions
        perms = self.registry.permission.get_objects_permissions(
            ["/buckets/chefclub-v2/collections/recipes"]
        )[0]
        # Should have source permissions (group:chefs), not old (admin)
        self.assertIn("read", perms)
        self.assertIn("group:chefs", str(perms))

    def test_rename_preserves_record_metadata(self):
        """Test that record metadata (modified timestamp, etc.) is preserved during rename."""
        # Get original record with all metadata
        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes2"

        # Get the original record details before rename
        orig_rec = self.registry.storage.get("record", src, "r1")
        # Verify original has timestamp
        self.assertIn("last_modified", orig_rec)

        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Get the renamed record and verify metadata
        new_rec = self.registry.storage.get("record", dst, "r1")
        self.assertEqual(new_rec["id"], "r1")
        self.assertEqual(new_rec["data"], "a")
        # The new record should have similar structure
        self.assertIn("last_modified", new_rec)

    def test_rename_handles_delete_failure_gracefully(self):
        """Test that rename continues even if some deletes fail (exception handlers)."""
        src = "/buckets/chefclub/collections/recipes"
        dst = "/buckets/chefclub-v2/collections/recipes2"

        # Mock storage to fail deletion of records during cleanup but succeed for collection
        original_delete = self.registry.storage.delete
        call_count = {"record": 0}

        def mock_delete(resource_name, parent_id, obj_id, **kwargs):
            # Make record deletions fail for source cleanup (lines 124-125, 129-130)
            if resource_name == "record" and parent_id == src and obj_id == "r1":
                # Record deletion during source cleanup - let it fail
                call_count["record"] += 1
                if call_count["record"] > 1:  # Let the first one succeed, fail subsequent ones
                    raise Exception("Mock deletion failure")
            return original_delete(resource_name, parent_id, obj_id, **kwargs)

        with mock.patch.object(self.registry.storage, "delete", side_effect=mock_delete):
            # Should not raise, should handle the exception
            res = rename_collection(self.env, src, dst)
            self.assertEqual(res, 0)

        # Verify destination has the record despite delete failures during source cleanup
        rec = self.registry.storage.get("record", dst, "r1")
        self.assertEqual(rec["id"], "r1")

    def test_rename_collection_with_no_src_permissions(self):
        """Test rename when source collection/records have empty permission lists."""
        # Create a collection without permissions set
        self.registry.storage.create("bucket", "", {"id": "no-perms"})
        self.registry.storage.create("collection", "/buckets/no-perms", {"id": "coll"})
        self.registry.storage.create(
            "record", "/buckets/no-perms/collections/coll", {"id": "rec1", "data": "x"}
        )

        src = "/buckets/no-perms/collections/coll"
        dst = "/buckets/chefclub-v2/collections/coll"

        res = rename_collection(self.env, src, dst)
        self.assertEqual(res, 0)

        # Verify move succeeded
        rec = self.registry.storage.get("record", dst, "rec1")
        self.assertEqual(rec["id"], "rec1")
