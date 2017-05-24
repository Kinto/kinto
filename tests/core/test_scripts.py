import mock

from kinto.core import scripts
from kinto.core.storage import Filter, Sort
from kinto.core.utils import COMPARISON
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

    def test_migrate_skips_missing_backends(self):
        class FakeRegistry:
            settings = dict()
            storage = mock.MagicMock()
        registry = FakeRegistry()
        scripts.migrate({'registry': registry})
        self.assertTrue(registry.storage.initialize_schema.called)

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

class RebuildQuotasTest(unittest.TestCase):
    OLDEST_FIRST = Sort('last_modified', 1)

    def setUp(self):
        self.registry = mock.MagicMock()

    def test_rebuild_quotas_in_read_only_display_an_error(self):
        with mock.patch('kinto.core.scripts.logger') as mocked:
            self.registry.settings = {'readonly': 'true'}
            code = scripts.rebuild_quotas({'registry': self.registry})
            assert code == 31
            mocked.error.assert_any_call('Cannot rebuild quotas while '
                                         'in readonly mode.')

    def test_rebuild_quotas_updates_records(self):
        paginated_data = [
            # get buckets
            iter([{"id": "bucket-1", "last_modified": 10}]),
            # get collections for first bucket
            iter([{"id": "collection-1", "last_modified": 100}, {"id": "collection-2", "last_modified": 200}]),
            # get records for first collection
            iter([{"id": "record-1", "last_modified": 110}]),
            # get records for second collection
            iter([{"id": "record-1b", "last_modified": 210}]),
        ]
        paginated_mock = lambda *args, **kwargs: paginated_data.pop(0)

        with mock.patch('kinto.core.scripts.logger') as mocked_logger:
            with mock.patch('kinto.core.scripts.paginated', side_effect=paginated_mock) as mocked_paginated:
                scripts.rebuild_quotas({'registry': self.registry})

        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='bucket',
            parent_id='',
            sorting=[self.OLDEST_FIRST],
            )
        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='collection',
            parent_id='/buckets/bucket-1',
            sorting=[self.OLDEST_FIRST],
            )
        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='record',
            parent_id='/buckets/bucket-1/collections/collection-1',
            sorting=[self.OLDEST_FIRST],
            )
        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='record',
            parent_id='/buckets/bucket-1/collections/collection-2',
            sorting=[self.OLDEST_FIRST],
            )
        self.registry.storage.update.assert_any_call(
            collection_id='quota',
            parent_id='/buckets/bucket-1',
            object_id='bucket_info',
            record={'record_count': 2, 'storage_size': 160})
        self.registry.storage.update.assert_any_call(
            collection_id='quota',
            parent_id='/buckets/bucket-1/collections/collection-1',
            object_id='collection_info',
            record={'record_count': 1, 'storage_size': 160})
        self.registry.storage.update.assert_any_call(
            collection_id='quota',
            parent_id='/buckets/bucket-1/collections/collection-2',
            object_id='collection_info',
            record={'record_count': 1, 'storage_size': 160})

        mocked.info.assert_any_call('Bucket bucket-1, collection collection-1. Final size: 1 records, 78 bytes.')
        mocked.info.assert_any_call('Bucket bucket-1, collection collection-2. Final size: 1 records, 79 bytes.')
        mocked.info.assert_any_call('Bucket bucket-1. Final size: 2 records, 193 bytes.')

    def test_rebuild_quotas_doesnt_update_if_dry_run(self):
        paginated_data = [
            # get buckets
            iter([{"id": "bucket-1", "last_modified": 10}]),
            # get collections for first bucket
            iter([{"id": "collection-1", "last_modified": 100}]),
            # get records for first collection
            iter([{"id": "record-1", "last_modified": 110}]),
        ]
        paginated_mock = lambda *args, **kwargs: paginated_data.pop(0)

        with mock.patch('kinto.core.scripts.logger') as mocked:
            with mock.patch('kinto.core.scripts.paginated', side_effect=paginated_mock) as mocked_paginated:
                scripts.rebuild_quotas({'registry': self.registry})

        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='bucket',
            parent_id='',
            sorting=[self.OLDEST_FIRST],
            )
        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='collection',
            parent_id='/buckets/bucket-1',
            sorting=[self.OLDEST_FIRST],
            )
        mocked_paginated.assert_any_call(
            self.registry.storage,
            collection_id='record',
            parent_id='/buckets/bucket-1/collections/collection-1',
            sorting=[self.OLDEST_FIRST],
            )
        assert not self.registry.storage.update.called

        mocked.info.assert_any_call('Bucket bucket-1, collection collection-1. Final size: 1 records, 78 bytes.')
        mocked.info.assert_any_call('Bucket bucket-1. Final size: 1 records, 114 bytes.')
