from .test_history import HistoryWebTest


class HistoryAtListViewTest(HistoryWebTest):

    def setUp(self):
        self.bucket_uri = '/buckets/test'
        self.app.put(self.bucket_uri, headers=self.headers)

        self.collection_uri = self.bucket_uri + '/collections/col'
        resp = self.app.put(self.collection_uri, headers=self.headers)
        self.collection = resp.json['data']

        self.group_uri = self.bucket_uri + '/groups/grp'
        body = {'data': {'members': ['elle']}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        self.group = resp.json['data']

        self.record_uri = '/buckets/test/collections/col/records/rec'
        body = {'data': {'foo': 42}}
        resp = self.app.put_json(self.record_uri, body, headers=self.headers)
        self.record = resp.json['data']

    def build_version_object_uri(self, object_url):
        return object_url + '/version'


class HistoryAtCollectionsViewTest(HistoryAtListViewTest):

    def test_we_can_get_a_bucket_collection_list_at_a_certain_time(self):
        # Create a second collection
        collection_2_uri = self.bucket_uri + '/collections/col2'
        resp = self.app.put(collection_2_uri, headers=self.headers)
        collection2 = resp.json['data']
        col2_creation_last_modified = collection2['last_modified']

        # Create a third collection
        collection_3_uri = self.bucket_uri + '/collections/col3'
        resp = self.app.put(collection_3_uri, headers=self.headers)
        collection3 = resp.json['data']
        col3_creation_last_modified = collection3['last_modified']

        # Check view at 1, 2 and 3
        bucket_collections_uri = self.build_version_object_uri(self.bucket_uri + '/collections')

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col2_creation_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection2, self.collection]

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col3_creation_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection3, collection2, self.collection]

    def test_we_can_get_a_bucket_collection_list_at_a_certain_time_with_deleted(self):
        # Create a second collection
        collection_2_uri = self.bucket_uri + '/collections/col2'
        resp = self.app.put(collection_2_uri, headers=self.headers)
        collection2 = resp.json['data']
        col2_creation_last_modified = collection2['last_modified']

        # Create a third collection
        collection_3_uri = self.bucket_uri + '/collections/col3'
        resp = self.app.put(collection_3_uri, headers=self.headers)
        collection3 = resp.json['data']
        col3_creation_last_modified = collection3['last_modified']

        # Delete collection 2
        resp = self.app.delete(collection_2_uri, headers=self.headers)
        col2_deletion_last_modified = resp.json['data']['last_modified']

        # Check view at 1, 2 and 3
        bucket_collections_uri = self.build_version_object_uri(self.bucket_uri + '/collections')

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col2_creation_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection2, self.collection]

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col3_creation_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection3, collection2, self.collection]

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col2_deletion_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection3, self.collection]

    def test_we_can_get_a_bucket_collection_list_at_a_certain_time_with_updated(self):
        # Create a second collection
        collection_2_uri = self.bucket_uri + '/collections/col2'
        resp = self.app.put(collection_2_uri, headers=self.headers)
        collection2 = resp.json['data']
        col2_creation_last_modified = collection2['last_modified']

        # Create a third collection
        collection_3_uri = self.bucket_uri + '/collections/col3'
        resp = self.app.put(collection_3_uri, headers=self.headers)
        collection3 = resp.json['data']
        col3_creation_last_modified = collection3['last_modified']

        # Update the first collection
        resp = self.app.patch_json(self.collection_uri,
                                   {"data": {"rock": "on"}},
                                   headers=self.headers)
        collection = resp.json['data']
        collection_update_last_modified = collection['last_modified']

        bucket_collections_uri = self.build_version_object_uri(self.bucket_uri + '/collections')

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col2_creation_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection2, self.collection]

        resp = self.app.get('{}/{}'.format(bucket_collections_uri, col3_creation_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection3, collection2, self.collection]

        resp = self.app.get('{}/{}'.format(bucket_collections_uri,
                                           collection_update_last_modified),
                            headers=self.headers)
        collections = resp.json['data']
        assert collections == [collection, collection3, collection2]


class HistoryAtGroupsViewTest(HistoryAtListViewTest):

    def test_we_can_get_a_bucket_group_list_at_a_certain_time(self):
        # Create a second group
        group_2_uri = self.bucket_uri + '/groups/group2'
        resp = self.app.put_json(group_2_uri,
                                 {"data": {"members": ["group2_member"]}},
                                 headers=self.headers)
        group2 = resp.json['data']
        group2_creation_last_modified = group2['last_modified']

        # Create a third group
        group_3_uri = self.bucket_uri + '/groups/group3'
        resp = self.app.put_json(group_3_uri,
                                 {"data": {"members": ["group3_member"]}},
                                 headers=self.headers)
        group3 = resp.json['data']
        group3_creation_last_modified = group3['last_modified']

        # Check view at 1, 2 and 3
        bucket_groups_uri = self.build_version_object_uri(self.bucket_uri + '/groups')

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group2_creation_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group2, self.group]

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group3_creation_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group3, group2, self.group]

    def test_we_can_get_a_bucket_group_list_at_a_certain_time_with_deleted(self):
        # Create a second group
        group_2_uri = self.bucket_uri + '/groups/group2'
        resp = self.app.put_json(group_2_uri,
                                 {"data": {"members": ["group2_member"]}},
                                 headers=self.headers)
        group2 = resp.json['data']
        group2_creation_last_modified = group2['last_modified']

        # Create a third group
        group_3_uri = self.bucket_uri + '/groups/group3'
        resp = self.app.put_json(group_3_uri,
                                 {"data": {"members": ["group3_member"]}},
                                 headers=self.headers)
        group3 = resp.json['data']
        group3_creation_last_modified = group3['last_modified']

        # Delete group 2
        resp = self.app.delete(group_2_uri, headers=self.headers)
        group2_deletion_last_modified = resp.json['data']['last_modified']

        # Check view at 1, 2 and 3
        bucket_groups_uri = self.build_version_object_uri(self.bucket_uri + '/groups')

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group2_creation_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group2, self.group]

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group3_creation_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group3, group2, self.group]

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group2_deletion_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group3, self.group]

    def test_we_can_get_a_bucket_group_list_at_a_certain_time_with_updated(self):
        # Create a second group
        group_2_uri = self.bucket_uri + '/groups/group2'
        resp = self.app.put_json(group_2_uri,
                                 {"data": {"members": ["group2_member"]}},
                                 headers=self.headers)
        group2 = resp.json['data']
        group2_creation_last_modified = group2['last_modified']

        # Create a third group
        group_3_uri = self.bucket_uri + '/groups/group3'
        resp = self.app.put_json(group_3_uri,
                                 {"data": {"members": ["group3_member"]}},
                                 headers=self.headers)
        group3 = resp.json['data']
        group3_creation_last_modified = group3['last_modified']

        # Update the first group
        resp = self.app.patch_json(self.group_uri,
                                   {"data": {"members": ['group1_member']}},
                                   headers=self.headers)
        group = resp.json['data']
        group_update_last_modified = group['last_modified']

        bucket_groups_uri = self.build_version_object_uri(self.bucket_uri + '/groups')

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group2_creation_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group2, self.group]

        resp = self.app.get('{}/{}'.format(bucket_groups_uri, group3_creation_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group3, group2, self.group]

        resp = self.app.get('{}/{}'.format(bucket_groups_uri,
                                           group_update_last_modified),
                            headers=self.headers)
        groups = resp.json['data']
        assert groups == [group, group3, group2]


class HistoryAtRecordsViewTest(HistoryAtListViewTest):

    def test_we_can_get_a_bucket_record_list_at_a_certain_time(self):
        # Create a second record
        record_2_uri = self.collection_uri + '/records/record2'
        resp = self.app.put_json(record_2_uri,
                                 {"data": {"foo": ["record2"]}},
                                 headers=self.headers)
        record2 = resp.json['data']
        record2_creation_last_modified = record2['last_modified']

        # Create a third record
        record_3_uri = self.collection_uri + '/records/record3'
        resp = self.app.put_json(record_3_uri,
                                 {"data": {"foo": ["record3"]}},
                                 headers=self.headers)
        record3 = resp.json['data']
        record3_creation_last_modified = record3['last_modified']

        # Check view at 1, 2 and 3
        bucket_records_uri = self.build_version_object_uri(self.collection_uri + '/records')

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record2_creation_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record2, self.record]

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record3_creation_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record3, record2, self.record]

    def test_we_can_get_a_bucket_record_list_at_a_certain_time_with_deleted(self):
        # Create a second record
        record_2_uri = self.collection_uri + '/records/record2'
        resp = self.app.put_json(record_2_uri,
                                 {"data": {"foo": ["record2"]}},
                                 headers=self.headers)
        record2 = resp.json['data']
        record2_creation_last_modified = record2['last_modified']

        # Create a third record
        record_3_uri = self.collection_uri + '/records/record3'
        resp = self.app.put_json(record_3_uri,
                                 {"data": {"foo": ["record3"]}},
                                 headers=self.headers)
        record3 = resp.json['data']
        record3_creation_last_modified = record3['last_modified']

        # Delete record 2
        resp = self.app.delete(record_2_uri, headers=self.headers)
        record2_deletion_last_modified = resp.json['data']['last_modified']

        # Check view at 1, 2 and 3
        bucket_records_uri = self.build_version_object_uri(self.collection_uri + '/records')

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record2_creation_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record2, self.record]

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record3_creation_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record3, record2, self.record]

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record2_deletion_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record3, self.record]

    def test_we_can_get_a_bucket_record_list_at_a_certain_time_with_updated(self):
        # Create a second record
        record_2_uri = self.collection_uri + '/records/record2'
        resp = self.app.put_json(record_2_uri,
                                 {"data": {"foo": ["record2"]}},
                                 headers=self.headers)
        record2 = resp.json['data']
        record2_creation_last_modified = record2['last_modified']

        # Create a third record
        record_3_uri = self.collection_uri + '/records/record3'
        resp = self.app.put_json(record_3_uri,
                                 {"data": {"foo": ["record3"]}},
                                 headers=self.headers)
        record3 = resp.json['data']
        record3_creation_last_modified = record3['last_modified']

        # Update the first record
        resp = self.app.patch_json(self.record_uri,
                                   {"data": {"foo": ['record1']}},
                                   headers=self.headers)
        record = resp.json['data']
        record_update_last_modified = record['last_modified']

        bucket_records_uri = self.build_version_object_uri(self.collection_uri + '/records')

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record2_creation_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record2, self.record]

        resp = self.app.get('{}/{}'.format(bucket_records_uri, record3_creation_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record3, record2, self.record]

        resp = self.app.get('{}/{}'.format(bucket_records_uri,
                                           record_update_last_modified),
                            headers=self.headers)
        records = resp.json['data']
        assert records == [record, record3, record2]
