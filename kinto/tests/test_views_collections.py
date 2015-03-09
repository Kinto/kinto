from .support import BaseWebTest, unittest, get_user_headers


MINIMALIST_ITEM = dict(name="Hulled Barley",
                       type="Whole Grain")


class CollectionViewTest(BaseWebTest, unittest.TestCase):
    def test_empty_collection_returns_an_empty_list(self):
        response = self.app.get('/collections/barley/records',
                                headers=self.headers)
        self.assertEqual(response.json['items'], [])

    def test_individual_collections_can_be_deleted(self):
        self.app.post('/collections/barley/records',
                      headers=self.headers)

        self.app.delete('/collections/barley/records',
                        headers=self.headers)

    def test_items_can_be_added_to_collections(self):
        response = self.app.post_json('/collections/barley/records',
                                      MINIMALIST_ITEM,
                                      headers=self.headers)
        _id = response.json.get('id')
        self.assertIsNotNone(_id)
        response = self.app.get('/collections/barley/records/%s' % _id,
                                headers=self.headers)

        item = response.json
        del item['id']
        del item['last_modified']
        self.assertEquals(item, MINIMALIST_ITEM)

    def test_collections_are_user_bound(self):
        # Add items in the collections.
        response = self.app.post_json('/collections/barley/records',
                                      MINIMALIST_ITEM,
                                      headers=self.headers)
        self.app.get('/collections/barley/records/%s' % response.json['id'],
                     headers=get_user_headers("alice"), status=404)

    def test_collection_items_can_be_accessed_by_id(self):
        response = self.app.post_json('/collections/barley/records',
                                      MINIMALIST_ITEM,
                                      headers=self.headers)
        self.app.get('/collections/barley/records/%s' % response.json['id'],
                     headers=self.headers)

    def test_collection_items_can_be_filtered_on_any_field(self):
        self.app.post_json('/collections/barley/records',
                           MINIMALIST_ITEM,
                           headers=self.headers)
        response = self.app.get('/collections/barley/records?unknown=1',
                                headers=self.headers)
        self.assertEqual(len(response.json['items']), 0)

    def test_collection_items_can_be_sorted_on_any_field(self):
        for i in range(3):
            record = MINIMALIST_ITEM.copy()
            record['name'] = 'Stout %s' % i
            self.app.post_json('/collections/barley/records',
                               record,
                               headers=self.headers)

        response = self.app.get('/collections/barley/records?_sort=-name',
                                headers=self.headers)
        names = [i['name'] for i in response.json['items']]
        self.assertEqual(names, ['Stout 2', 'Stout 1', 'Stout 0'])
