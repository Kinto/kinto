from .test_history import HistoryWebTest


class HistoryAtCollectionViewTest(HistoryWebTest):

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

    def test_we_can_get_a_bucket_at_a_certain_time(self):
        # 1. Create a second collection
        collection_2_uri = self.bucket_uri + '/collections/col2'
        resp = self.app.put(collection_2_uri, headers=self.headers)
        collection2 = resp.json['data']
        col2_creation_last_modified = collection2['last_modified']

        # 2. Create a third collection
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
