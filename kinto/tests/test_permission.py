from kinto import permission

from .support import unittest


class PermissionTest(unittest.TestCase):
    record_uri = '/buckets/blog/collections/articles/records/article1'
    collection_uri = '/buckets/blog/collections/articles'
    group_uri = '/buckets/blog/groups/moderators'
    bucket_uri = '/buckets/blog'
    invalid_uri = 'invalid object id'

    def test_get_object_type_return_right_type_for_key(self):
        self.assertEqual(permission.get_object_type(self.record_uri), 'record')
        self.assertEqual(permission.get_object_type(self.collection_uri),
                         'collection')
        self.assertEqual(permission.get_object_type(self.bucket_uri), 'bucket')
        self.assertEqual(permission.get_object_type(self.group_uri), 'group')
        self.assertRaises(ValueError, permission.get_object_type,
                          self.invalid_uri)

    def test_build_perm_set_uri_can_construct_parents_set_uris(self):
        obj_parts = self.record_uri.split('/')
        # Can build record_uri from obj_parts
        self.assertEqual(
            permission.build_permission_tuple('record', 'write', obj_parts),
            (self.record_uri, 'write'))

        # Can build collection_uri from obj_parts
        self.assertEqual(
            permission.build_permission_tuple('collection', 'records:create',
                                              obj_parts),
            (self.collection_uri, 'records:create'))

        # Can build bucket_uri from obj_parts
        self.assertEqual(permission.build_permission_tuple(
            'bucket', 'groups:create', obj_parts),
            (self.bucket_uri, 'groups:create'))

        # Can build group_uri from group obj_parts
        obj_parts = self.group_uri.split('/')
        self.assertEqual(permission.build_permission_tuple(
            'group', 'read', obj_parts),
            (self.group_uri, 'read'))

        # Can build bucket_uri from group obj_parts
        obj_parts = self.group_uri.split('/')
        self.assertEqual(permission.build_permission_tuple(
            'bucket', 'write', obj_parts),
            (self.bucket_uri, 'write'))

    def test_build_permission_tuple_fail_construct_children_set_uris(self):
        obj_parts = self.bucket_uri.split('/')
        # Cannot build record_uri from bucket obj_parts
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'record', 'write', obj_parts)

        # Cannot build collection_uri from obj_parts
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'collection', 'write', obj_parts)

        # Cannot build bucket_uri from empty obj_parts
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'collection', 'write', [])

    def test_build_permission_tuple_fail_on_wrong_type(self):
        obj_parts = self.record_uri.split('/')
        self.assertRaises(ValueError,
                          permission.build_permission_tuple,
                          'schema', 'write', obj_parts)

    def test_get_perm_keys_for_bucket_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.bucket_uri, 'write'),
            set([(self.bucket_uri, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.bucket_uri, 'read'),
            set([(self.bucket_uri, 'write'), (self.bucket_uri, 'read')]))

        # groups:create
        self.assertEquals(
            permission.build_permissions_set(self.bucket_uri, 'groups:create'),
            set(
                [(self.bucket_uri, 'write'), (self.bucket_uri, 'groups:create')])
            )

        # collections:create
        self.assertEquals(
            permission.build_permissions_set(self.bucket_uri,
                                             'collections:create'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'collections:create')]))

    def test_build_permissions_set_for_group_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.group_uri, 'write'),
            set([(self.bucket_uri, 'write'),
                 (self.group_uri, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.group_uri, 'read'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.group_uri, 'write'),
                 (self.group_uri, 'read')]))

    def test_build_permissions_set_for_collection_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.collection_uri, 'write'),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.collection_uri, 'read'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'read')]))
        # records:create
        self.assertEquals(
            permission.build_permissions_set(self.collection_uri,
                                             'records:create'),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'records:create')]))

    def test_build_permissions_set_for_record_permission(self):
        # write
        self.assertEquals(
            permission.build_permissions_set(self.record_uri, 'write'),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write'),
                 (self.record_uri, 'write')]))
        # read
        self.assertEquals(
            permission.build_permissions_set(self.record_uri, 'read'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'read'),
                 (self.record_uri, 'write'),
                 (self.record_uri, 'read')]))
