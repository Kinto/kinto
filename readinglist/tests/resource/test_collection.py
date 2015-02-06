from pyramid import httpexceptions

from readinglist.tests.resource import BaseTest


class CollectionTest(BaseTest):
    def setUp(self):
        super(CollectionTest, self).setUp()
        self.record = self.db.create(self.resource, 'bob', {'field': 'value'})

    def test_list_gives_number_of_results_in_headers(self):
        self.resource.collection_get()
        headers = self.last_response.headers
        count = headers['Total-Records']
        self.assertEquals(int(count), 1)

    def test_list_returns_all_records_in_items(self):
        result = self.resource.collection_get()
        records = result['items']
        self.assertEqual(len(records), 1)
        self.assertDictEqual(records[0], self.record)


class CreateTest(BaseTest):
    def test_new_records_are_linked_to_owner(self):
        resp = self.resource.collection_post()
        record_id = resp['id']
        self.db.get(self.resource, 'bob', record_id)  # not raising

    def test_create_record_returns_at_least_id_and_last_modified(self):
        self.resource.request.validated = {'field': 'value'}
        record = self.resource.collection_post()
        self.assertIn(self.resource.id_field, record)
        self.assertIn(self.resource.modified_field, record)
        self.assertIn('field', record)


class IsolatedCollectionsTest(BaseTest):
    def setUp(self):
        super(IsolatedCollectionsTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})
        self.resource.request.matchdict['id'] = self.stored['id']

    def get_request(self):
        request = super(IsolatedCollectionsTest, self).get_request()
        request.authenticated_userid = 'alice'
        return request

    def test_list_is_filtered_by_user(self):
        resp = self.resource.collection_get()
        records = resp['items']
        self.assertEquals(len(records), 0)

    def test_update_record_of_another_user_will_create_it(self):
        self.resource.request.validated = {'some': 'record'}
        self.resource.put()
        self.db.get(self.resource, 'alice', self.stored['id'])  # not raising

    def test_cannot_modify_record_of_other_user(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.patch)

    def test_cannot_delete_record_of_other_user(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.delete)
