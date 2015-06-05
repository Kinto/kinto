from .support import BaseWebTest, unittest


MINIMALIST_ITEM = dict(name="Hulled Barley",
                       type="Whole Grain")


class RecordsViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'
    record_url = '/buckets/beers/collections/barley/records/%s'

    def test_empty_collection_returns_an_empty_list(self):
        response = self.app.get(self.collection_url, headers=self.headers)
        self.assertEqual(response.json['items'], [])

    def test_individual_collections_can_be_deleted(self):
        self.app.post(self.collection_url, headers=self.headers)
        self.app.delete(self.collection_url, headers=self.headers)

    def test_records_can_be_added_to_collections(self):
        response = self.app.post_json(self.collection_url,
                                      MINIMALIST_ITEM,
                                      headers=self.headers)
        _id = response.json.get('id')
        self.assertIsNotNone(_id)
        response = self.app.get(self.record_url % _id, headers=self.headers)

        item = response.json
        del item['id']
        del item['last_modified']
        self.assertEquals(item, MINIMALIST_ITEM)

    def test_records_are_isolated_by_bucket_and_by_collection(self):
        response = self.app.post_json(self.collection_url,
                                      MINIMALIST_ITEM,
                                      headers=self.headers)
        record_url = self.record_url % response.json['id']

        other_collection = record_url.replace('barley', 'pills')
        self.app.get(other_collection, headers=self.headers, status=404)

        other_bucket = record_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=404)

        other = record_url.replace('barley', 'pills').replace('beers', 'sodas')
        self.app.get(other, headers=self.headers, status=404)

    def test_a_collection_named_group_do_not_interfere_with_groups(self):
        # Create a group.
        self.app.put_json('/buckets/beers/groups/test',
                          {'members': ['fxa:user']},
                          headers=self.headers)
        # Create a record in a collection named "group".
        collection_group = self.collection_url.replace('barley', 'groups')
        self.app.post_json(collection_group,
                           MINIMALIST_ITEM,
                           headers=self.headers)
        # There is still only one group.
        resp = self.app.get('/buckets/beers/groups', headers=self.headers)
        self.assertEqual(len(resp.json['items']), 1)

    def test_records_can_be_accessed_by_id(self):
        response = self.app.post_json(self.collection_url,
                                      MINIMALIST_ITEM,
                                      headers=self.headers)
        self.app.get(self.record_url % response.json['id'],
                     headers=self.headers)

    def test_records_can_be_filtered_on_any_field(self):
        self.app.post_json(self.collection_url,
                           MINIMALIST_ITEM,
                           headers=self.headers)
        response = self.app.get(self.collection_url + '?unknown=1',
                                headers=self.headers)
        self.assertEqual(len(response.json['items']), 0)

    def test_records_can_be_sorted_on_any_field(self):
        for i in range(3):
            record = MINIMALIST_ITEM.copy()
            record['name'] = 'Stout %s' % i
            self.app.post_json(self.collection_url,
                               record,
                               headers=self.headers)

        response = self.app.get(self.collection_url + '?_sort=-name',
                                headers=self.headers)
        names = [i['name'] for i in response.json['items']]
        self.assertEqual(names, ['Stout 2', 'Stout 1', 'Stout 0'])
