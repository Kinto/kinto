import mock

from kinto.core import scripts
from kinto.core.storage.exceptions import RecordNotFoundError
from kinto.core.testing import unittest


class InitSchemaTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()

    def test_migrate_calls_initialize_schema_on_backends(self):
        scripts.migrate({'registry': self.registry})
        self.assertTrue(self.registry.storage.initialize_schema.called)
        self.assertTrue(self.registry.cache.initialize_schema.called)
        self.assertTrue(self.registry.permission.initialize_schema.called)

    def test_migrate_in_read_only_display_an_error(self):
        with mock.patch('kinto.core.scripts.logger') as mocked:
            self.registry.settings = {'readonly': 'true'}
            scripts.migrate({'registry': self.registry})
            mocked.error.assert_any_call('Cannot migrate the storage backend '
                                         'while in readonly mode.')
            mocked.error.assert_any_call('Cannot migrate the permission '
                                         'backend while in readonly mode.')

    def test_migrate_in_dry_run_mode(self):
        scripts.migrate({'registry': self.registry}, dry_run=True)
        reg = self.registry
        reg.storage.initialize_schema.assert_called_with(dry_run=True)
        reg.cache.initialize_schema.assert_called_with(dry_run=True)
        reg.permission.initialize_schema.assert_called_with(dry_run=True)


class DeleteCollectionTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()

    def test_delete_collection_in_read_only_display_an_error(self):
        with mock.patch('kinto.core.scripts.logger') as mocked:
            self.registry.settings = {'readonly': 'true'}
            code = scripts.delete_collection({'registry': self.registry},
                                             'test_bucket',
                                             'test_collection')
            assert code == 31
            mocked.error.assert_any_call('Cannot delete the collection while '
                                         'in readonly mode.')

    def test_delete_collection_remove_collection_records(self):
        self.registry.storage.delete_all.return_value = [
            {"id": "1234"}, {"id": "5678"}
        ]

        with mock.patch('kinto.core.scripts.logger') as mocked:
            scripts.delete_collection({'registry': self.registry},
                                      'test_bucket',
                                      'test_collection')

        self.registry.storage.delete_all.assert_called_with(
            collection_id='record',
            parent_id='/buckets/test_bucket/collections/test_collection',
            with_deleted=False)
        self.registry.storage.delete.assert_called_with(
            collection_id='collection',
            parent_id='/buckets/test_bucket',
            object_id='test_collection',
            with_deleted=False)
        self.registry.permission.delete_object_permissions.assert_called_with(
            '/buckets/test_bucket/collections/test_collection',
            '/buckets/test_bucket/collections/test_collection/records/1234',
            '/buckets/test_bucket/collections/test_collection/records/5678')

        mocked.info.assert_any_call('2 record(s) were deleted.')
        mocked.info.assert_any_call(
            "'/buckets/test_bucket/collections/test_collection' "
            "collection object was deleted.")

    def test_delete_collection_tell_when_no_records_where_found(self):
        self.registry.storage.delete_all.return_value = []

        with mock.patch('kinto.core.scripts.logger') as mocked:
            scripts.delete_collection({'registry': self.registry},
                                      'test_bucket',
                                      'test_collection')

        mocked.info.assert_any_call(
            "No records found for "
            "'/buckets/test_bucket/collections/test_collection'.")
        mocked.info.assert_any_call(
            "'/buckets/test_bucket/collections/test_collection' "
            "collection object was deleted.")
        mocked.info.assert_any_call("Related permissions were deleted.")

    def test_delete_collection_raise_if_the_bucket_does_not_exist(self):
        self.registry.storage.get.side_effect = RecordNotFoundError
        with mock.patch('kinto.core.scripts.logger') as mocked:
            resp = scripts.delete_collection({'registry': self.registry},
                                             'test_bucket',
                                             'test_collection')
        assert resp == 32
        mocked.error.assert_called_with(
            "Bucket '/buckets/test_bucket' does not exist.")

    def test_delete_collection_raise_if_the_collection_does_not_exist(self):
        self.registry.storage.get.side_effect = ['', RecordNotFoundError]
        with mock.patch('kinto.core.scripts.logger') as mocked:
            resp = scripts.delete_collection({'registry': self.registry},
                                             'test_bucket',
                                             'test_collection')
        assert resp == 33
        mocked.error.assert_called_with(
            "Collection '/buckets/test_bucket/collections/test_collection' "
            "does not exist.")
