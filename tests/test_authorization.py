from kinto.core.testing import unittest

from kinto.authorization import (_resource_endpoint, _relative_object_uri,
                                 _inherited_permissions)


class ResourceEndpointTest(unittest.TestCase):
    def test_resource_endpoint_return_right_type_for_key(self):
        self.assertEqual(_resource_endpoint('/buckets/bid/collections/cid/records/rid'),
                         ('record', False))
        self.assertEqual(_resource_endpoint('/buckets/bid/collections/cid'),
                         ('collection', False))
        self.assertEqual(_resource_endpoint('/buckets'), ('', False))
        self.assertEqual(_resource_endpoint('/buckets/bid'), ('bucket', False))
        self.assertEqual(_resource_endpoint('/buckets/bid/history/xx'), ('history', False))
        self.assertEqual(_resource_endpoint('/buckets/bid/groups/moderators'),
                         ('group', False))

    def test_resource_endpoint_return_right_type_for_children_collection(self):
        self.assertEqual(_resource_endpoint('/buckets/bid/collections/cid/records'),
                         ('collection', True))
        self.assertEqual(_resource_endpoint('/buckets/bid/collections'), ('bucket', True))
        self.assertEqual(_resource_endpoint('/buckets/bid/history'), ('bucket', True))
        self.assertEqual(_resource_endpoint('/buckets/bid/groups'), ('bucket', True))


class RelativeObjectUri(unittest.TestCase):
    record_uri = '/buckets/blog/collections/articles/records/article1'
    records_uri = '/buckets/blog/collections/articles/records'
    collection_uri = '/buckets/blog/collections/articles'
    collections_uri = '/buckets/blog/collections'
    group_uri = '/buckets/blog/groups/moderators'
    groups_uri = '/buckets/blog/groups'
    bucket_uri = '/buckets/blog'
    buckets_uri = '/buckets'

    def test_related_object_uri_can_construct_parents_set_uris(self):
        record_uri = '/buckets/bid/collections/cid/records/rid'
        self.assertEqual(_relative_object_uri('record', record_uri), record_uri)

        self.assertEqual(_relative_object_uri('collection', self.record_uri),
                         self.collection_uri)
        self.assertEqual(_relative_object_uri('collection', self.records_uri),
                         self.collection_uri)

        # Can build bucket_uri from obj_parts
        self.assertEqual(_relative_object_uri('bucket', self.record_uri),
                         self.bucket_uri)

        # Can build group_uri from group obj_parts
        self.assertEqual(_relative_object_uri('group', self.group_uri),
                         self.group_uri)

        # Can build bucket_uri from group obj_parts
        self.assertEqual(_relative_object_uri('bucket', self.group_uri),
                         self.bucket_uri)
        self.assertEqual(_relative_object_uri('bucket', self.groups_uri),
                         self.bucket_uri)

    def test_relative_object_uri_fail_construct_children_set_uris(self):
        # Cannot build record_uri from bucket obj_parts
        self.assertRaises(ValueError,
                          _relative_object_uri,
                          'record', self.bucket_uri)

        # Cannot build collection_uri from obj_parts
        self.assertRaises(ValueError,
                          _relative_object_uri,
                          'collection', self.bucket_uri)

        # Cannot build bucket_uri from empty obj_parts
        self.assertRaises(ValueError,
                          _relative_object_uri,
                          'collection', '')


class PermissionInheritanceTest(unittest.TestCase):
    record_uri = '/buckets/blog/collections/articles/records/article1'
    collection_uri = '/buckets/blog/collections/articles'
    group_uri = '/buckets/blog/groups/moderators'
    bucket_uri = '/buckets/blog'

    def test_relative_object_uri_fail_on_wrong_type(self):
        self.assertRaises(ValueError,
                          _relative_object_uri,
                          'schema', self.record_uri)

    def test_inherited_permissions_supports_buckets_named_collections(self):
        uri = '/buckets/collections'
        self.assertEquals(set(_inherited_permissions(uri, 'write')),
                          set([(uri, 'write')]))

    def test_inherited_permissions_for_bucket_permission(self):
        # write
        self.assertEquals(
            _inherited_permissions(self.bucket_uri, 'write'),
            [(self.bucket_uri, 'write')])
        # read
        self.assertEquals(
            set(_inherited_permissions(self.bucket_uri, 'read')),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.bucket_uri, 'collection:create'),
                 (self.bucket_uri, 'group:create')]))

        # group:create
        groups_uri = self.bucket_uri + '/groups'
        self.assertEquals(
            set(_inherited_permissions(groups_uri, 'group:create')),
            set(
                [(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'group:create')])
            )

        # collection:create
        collections_uri = self.bucket_uri + '/collections'
        self.assertEquals(
            set(_inherited_permissions(collections_uri, 'collection:create')),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'collection:create')]))

    def test_inherited_permissions_for_group_permission(self):
        # write
        self.assertEquals(
            _inherited_permissions(self.group_uri, 'write'),
            [(self.group_uri, 'write'),
             (self.bucket_uri, 'write')])
        # read
        self.assertEquals(
            set(_inherited_permissions(self.group_uri, 'read')),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.group_uri, 'write'),
                 (self.group_uri, 'read')]))

    def test_inherited_permissions_for_collection_permission(self):
        # write
        self.assertEquals(
            _inherited_permissions(self.collection_uri, 'write'),
            [(self.collection_uri, 'write'),
             (self.bucket_uri, 'write')])
        # read
        self.assertEquals(
            set(_inherited_permissions(self.collection_uri, 'read')),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'read'),
                 (self.collection_uri, 'record:create')]))
        # records:create
        records_uri = self.collection_uri + '/records'
        self.assertEquals(
            set(_inherited_permissions(records_uri, 'record:create')),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'record:create')]))

    def test_inherited_permissions_for_record_permission(self):
        # write
        self.assertEquals(
            set(_inherited_permissions(self.record_uri, 'write')),
            set([(self.bucket_uri, 'write'),
                 (self.collection_uri, 'write'),
                 (self.record_uri, 'write')]))
        # read
        self.assertEquals(
            set(_inherited_permissions(self.record_uri, 'read')),
            set([(self.bucket_uri, 'write'),
                 (self.bucket_uri, 'read'),
                 (self.collection_uri, 'write'),
                 (self.collection_uri, 'read'),
                 (self.record_uri, 'write'),
                 (self.record_uri, 'read')]))

    def test_inherited_permissions_for_list_of_buckets(self):
        permissions = _inherited_permissions('/buckets', 'read')
        self.assertEquals(permissions, [])

    def test_inherited_permissions_for_non_resource_url(self):
        unknown = '/resource/unknown'
        permissions = _inherited_permissions(unknown, 'read')
        self.assertEquals(permissions, [])

    def test_inherited_permissions_for_attachment_url(self):
        attachment = '/buckets/bid/collections/cid/records/rid/attachment'
        permissions = _inherited_permissions(attachment, 'read')
        self.assertIn(('/buckets/bid/collections/cid/records/rid', 'read'), permissions)
