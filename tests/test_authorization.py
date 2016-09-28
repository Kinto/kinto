from kinto.core.testing import unittest

from kinto.authorization import (_resource_endpoint, relative_object_uri,
                                 build_permissions_set)


class PermissionInheritanceTest(unittest.TestCase):
    record_uri = '/buckets/blog/collections/articles/records/article1'
    collection_uri = '/buckets/blog/collections/articles'
    group_uri = '/buckets/blog/groups/moderators'
    bucket_uri = '/buckets/blog'
    invalid_uri = 'invalid object id'

    def test_resource_endpoint_return_right_type_for_key(self):
        self.assertEqual(_resource_endpoint(self.record_uri), ('record', False))
        self.assertEqual(_resource_endpoint(self.collection_uri), ('collection', False))
        self.assertEqual(_resource_endpoint(self.bucket_uri), ('bucket', False))
        self.assertEqual(_resource_endpoint(self.group_uri), ('group', False))
        self.assertEqual(_resource_endpoint(self.invalid_uri), (None, None))

    def test_resource_endpoint_return_right_type_for_children_collection(self):
        self.assertEqual(_resource_endpoint(self.collection_uri + '/records'),
                         ('collection', True))
        self.assertEqual(_resource_endpoint(self.bucket_uri + '/collections'),
                         ('bucket', True))
        self.assertEqual(_resource_endpoint(self.bucket_uri + '/groups'),
                         ('bucket', True))

    def test_build_perm_set_uri_can_construct_parents_set_uris(self):
        # Can build record_uri from obj_parts
        self.assertEqual(relative_object_uri('record', self.record_uri),
                         self.record_uri)

        # Can build collection_uri from obj_parts
        self.assertEqual(relative_object_uri('collection', self.record_uri),
                         self.collection_uri)

        # Can build bucket_uri from obj_parts
        self.assertEqual(relative_object_uri('bucket', self.record_uri),
                         self.bucket_uri)

        # Can build group_uri from group obj_parts
        self.assertEqual(relative_object_uri('group', self.group_uri),
                         self.group_uri)

        # Can build bucket_uri from group obj_parts
        self.assertEqual(relative_object_uri('bucket', self.group_uri),
                         self.bucket_uri)

    def test_build_perm_set_supports_buckets_named_collections(self):
        uri = '/buckets/collections'
        self.assertEquals(build_permissions_set(uri, 'write'),
                          set([(uri, 'write')]))

    def test_relative_object_uri_fail_construct_children_set_uris(self):
        # Cannot build record_uri from bucket obj_parts
        self.assertRaises(ValueError,
                          relative_object_uri,
                          'record', self.bucket_uri)

        # Cannot build collection_uri from obj_parts
        self.assertRaises(ValueError,
                          relative_object_uri,
                          'collection', self.bucket_uri)

        # Cannot build bucket_uri from empty obj_parts
        self.assertRaises(ValueError,
                          relative_object_uri,
                          'collection', '')

    def test_relative_object_uri_fail_on_wrong_type(self):
        self.assertRaises(ValueError,
                          relative_object_uri,
                          'schema', self.record_uri)

    def test_get_perm_keys_for_bucket_permission(self):
        # write
        self.assertEquals(
            build_permissions_set(self.bucket_uri, 'write'),
            set([(self.bucket_uri, 'write')]))
        # read
        self.assertEquals(
            build_permissions_set(self.bucket_uri, 'read'),
            set([(self.bucket_uri, 'write'), (self.bucket_uri, 'read'),
                 (self.bucket_uri, 'collection:create'), (self.bucket_uri, 'group:create')]))

        # group:create
        groups_uri = self.bucket_uri + '/groups'
        self.assertEquals(
            build_permissions_set(groups_uri, 'group:create'),
            set(
                [(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'group:create')])
            )

        # collection:create
        collections_uri = self.bucket_uri + '/collections'
        self.assertEquals(
            build_permissions_set(collections_uri, 'collection:create'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'collection:create')]))

    def test_build_permissions_set_for_group_permission(self):
        # write
        self.assertEquals(
            build_permissions_set(self.group_uri, 'write'),
            set([(self.bucket_uri, 'write'),
                 (self.group_uri, 'write')]))
        # read
        self.assertEquals(
            build_permissions_set(self.group_uri, 'read'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.group_uri, 'write'),
                 (self.group_uri, 'read')]))

    def test_build_permissions_set_for_collection_permission(self):
        # write
        self.assertEquals(
            build_permissions_set(self.collection_uri, 'write'),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write')]))
        # read
        self.assertEquals(
            build_permissions_set(self.collection_uri, 'read'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'read'),
                 (self.collection_uri, 'record:create')]))
        # records:create
        records_uri = self.collection_uri + '/records'
        self.assertEquals(
            build_permissions_set(records_uri, 'record:create'),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'record:create')]))

    def test_build_permissions_set_for_record_permission(self):
        # write
        self.assertEquals(
            build_permissions_set(self.record_uri, 'write'),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write'),
                 (self.record_uri, 'write')]))
        # read
        self.assertEquals(
            build_permissions_set(self.record_uri, 'read'),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'read'),
                 (self.record_uri, 'write'),
                 (self.record_uri, 'read')]))

    def test_build_permissions_set_returns_empty_set_if_doesnt_know(self):
        permissions = build_permissions_set('/buckets', 'read')
        self.assertEquals(permissions, set())
