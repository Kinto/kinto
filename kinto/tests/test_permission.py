from kinto import permission

from .support import unittest


class PermissionTest(unittest.TestCase):
    record_id = '/buckets/blog/collections/articles/records/article1'
    collection_id = '/buckets/blog/collections/articles'
    group_id = '/buckets/blog/groups/moderators'
    bucket_id = '/buckets/blog'
    invalid_id = 'invalid object id'

    def test_get_object_type_return_right_type_for_key(self):
        self.assertEqual(permission.get_object_type(self.record_id), 'record')
        self.assertEqual(permission.get_object_type(self.collection_id),
                         'collection')
        self.assertEqual(permission.get_object_type(self.bucket_id), 'bucket')
        self.assertEqual(permission.get_object_type(self.group_id), 'group')
        self.assertRaises(ValueError, permission.get_object_type,
                          self.invalid_id)

    def test_build_perm_set_id_can_construct_parents_set_ids(self):
        obj_parts = self.record_id.split('/')
        # Can build record_id from obj_parts
        self.assertEqual(
            permission.build_permission_tuple('record', 'write', obj_parts),
            (self.record_id, 'write'))

        # Can build collection_id from obj_parts
        self.assertEqual(
            permission.build_permission_tuple('collection', 'records:create',
                                              obj_parts),
            (self.collection_id, 'records:create'))

        # Can build bucket_id from obj_parts
        self.assertEqual(permission.build_permission_tuple(
            'bucket', 'groups:create', obj_parts),
            (self.bucket_id, 'groups:create'))

        # Can build group_id from group obj_parts
        obj_parts = self.group_id.split('/')
        self.assertEqual(permission.build_permission_tuple(
            'group', 'read', obj_parts),
            (self.group_id, 'read'))

        # Can build bucket_id from group obj_parts
        obj_parts = self.group_id.split('/')
        self.assertEqual(permission.build_permission_tuple(
            'bucket', 'write', obj_parts),
            (self.bucket_id, 'write'))

    def test_build_permission_tuple_fail_construct_children_set_ids(self):
        obj_parts = self.bucket_id.split('/')
        # Cannot build record_id from bucket obj_parts
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'record', 'write', obj_parts)

        # Cannot build collection_id from obj_parts
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'collection', 'write', obj_parts)

        # Cannot build bucket_id from empty obj_parts
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'collection', 'write', [])

    def test_build_permission_tuple_fail_on_wrong_type(self):
        obj_parts = self.record_id.split('/')
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'schema', 'write', obj_parts)

    def test_get_perm_keys_for_bucket_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.bucket_id, 'write'),
            set([(self.bucket_id, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.bucket_id, 'read'),
            set([(self.bucket_id, 'write'), (self.bucket_id, 'read')]))

        # groups:create
        self.assertEquals(
            permission.build_permissions_set(self.bucket_id, 'groups:create'),
            set(
                [(self.bucket_id, 'write'), (self.bucket_id, 'groups:create')])
            )

        # collections:create
        self.assertEquals(
            permission.build_permissions_set(self.bucket_id,
                                             'collections:create'),
            set([(self.bucket_id, 'write'),
                 (self.bucket_id, 'collections:create')]))

    def test_build_permissions_set_for_group_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.group_id, 'write'),
            set([(self.bucket_id, 'write'),
                 (self.group_id, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.group_id, 'read'),
            set([(self.bucket_id, 'write'),
                 (self.bucket_id, 'read'),
                 (self.group_id, 'write'),
                 (self.group_id, 'read')]))

    def test_build_permissions_set_for_collection_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.collection_id, 'write'),
            set([(self.bucket_id, 'write'),
                 (self.collection_id, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.collection_id, 'read'),
            set([(self.bucket_id, 'write'),
                 (self.bucket_id, 'read'),
                 (self.collection_id, 'write'),
                 (self.collection_id, 'read')]))
        # records:create
        self.assertEquals(
            permission.build_permissions_set(self.collection_id,
                                             'records:create'),
            set([(self.bucket_id, 'write'),
                 (self.collection_id, 'write'),
                 (self.collection_id, 'records:create')]))

    def test_build_permissions_set_for_record_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.record_id, 'write'),
            set([(self.bucket_id, 'write'),
                 (self.collection_id, 'write'),
                 (self.record_id, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.record_id, 'read'),
            set([(self.bucket_id, 'write'),
                 (self.bucket_id, 'read'),
                 (self.collection_id, 'write'),
                 (self.collection_id, 'read'),
                 (self.record_id, 'write'),
                 (self.record_id, 'read')]))
