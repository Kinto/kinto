from .support import (BaseWebTest, unittest, MINIMALIST_RECORD,
                      MINIMALIST_GROUP, MINIMALIST_BUCKET,
                      MINIMALIST_COLLECTION)


class RecordsViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'
    _record_url = '/buckets/beers/collections/barley/records/%s'

    def setUp(self):
        super(RecordsViewTest, self).setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self._record_url % self.record['id']

    def test_records_can_be_accessed_by_id(self):
        self.app.get(self.record_url, headers=self.headers)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_unknown_collection_raises_404(self):
        other_collection = self.collection_url.replace('barley', 'pills')
        self.app.get(other_collection, headers=self.headers, status=404)

    def test_individual_collections_can_be_deleted(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)
        self.app.delete(self.collection_url, headers=self.headers)
        resp = self.app.get(self.collection_url, headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_records_can_be_added_to_collections(self):
        response = self.app.get(self.record_url, headers=self.headers)
        record = response.json['data']
        del record['id']
        del record['last_modified']
        self.assertEquals(record, MINIMALIST_RECORD['data'])

    def test_records_are_isolated_by_bucket_and_by_collection(self):
        # By collection.
        self.app.put_json('/buckets/beers/collections/pills',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        other_collection = self.record_url.replace('barley', 'pills')
        self.app.get(other_collection, headers=self.headers, status=404)

        # By bucket.
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/sodas/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        other_bucket = self.record_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=404)

        # By bucket and by collection.
        self.app.put_json('/buckets/be',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/be/collections/ba',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        other = self.record_url.replace('barley', 'ba').replace('beers', 'be')
        self.app.get(other, headers=self.headers, status=404)

    def test_a_collection_named_group_do_not_interfere_with_groups(self):
        # Create a group.
        self.app.put_json('/buckets/beers/groups/test',
                          MINIMALIST_GROUP,
                          headers=self.headers)
        # Create a record in a collection named "group".
        self.app.put_json('/buckets/beers/collections/groups',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)
        collection_group = self.collection_url.replace('barley', 'groups')
        self.app.post_json(collection_group,
                           MINIMALIST_RECORD,
                           headers=self.headers)
        # There is still only one group.
        resp = self.app.get('/buckets/beers/groups', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)

    def test_records_can_be_filtered_on_any_field(self):
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.headers)
        response = self.app.get(self.collection_url + '?unknown=1',
                                headers=self.headers)
        self.assertEqual(len(response.json['data']), 0)

    def test_records_can_be_sorted_on_any_field(self):
        for i in range(3):
            record = MINIMALIST_RECORD.copy()
            record['data']['name'] = 'Stout %s' % i
            self.app.post_json(self.collection_url,
                               record,
                               headers=self.headers)

        response = self.app.get(self.collection_url + '?_sort=-name',
                                headers=self.headers)
        names = [i['name'] for i in response.json['data']]
        self.assertEqual(names,
                         ['Stout 2', 'Stout 1', 'Stout 0', 'Hulled Barley'])

    def test_wrong_create_permissions_cannot_be_added_on_records(self):
        record = MINIMALIST_RECORD.copy()
        record['permissions'] = {'record:create': ['fxa:user']}
        self.app.put_json(self.record_url,
                          record,
                          headers=self.headers,
                          status=400)
