import unittest
from types import SimpleNamespace

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
