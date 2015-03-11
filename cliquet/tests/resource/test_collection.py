import mock
from pyramid import httpexceptions

from cliquet.tests.resource import BaseTest


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


class DeleteCollectionTest(BaseTest):
    def setUp(self):
        super(DeleteCollectionTest, self).setUp()
        self.patch_known_field.start()
        self.db.create(self.resource, 'bob', {'field': 'a'})
        self.db.create(self.resource, 'bob', {'field': 'b'})

    def test_delete_on_list_removes_all_records(self):
        self.resource.collection_delete()
        result = self.resource.collection_get()
        records = result['items']
        self.assertEqual(len(records), 0)

    def test_delete_returns_deleted_version_of_records(self):
        result = self.resource.collection_delete()
        deleted = result['items'][0]
        self.assertIn('deleted', deleted)

    def test_delete_supports_collection_filters(self):
        self.resource.request.GET = {'field': 'a'}
        self.resource.collection_delete()
        self.resource.request.GET = {}
        result = self.resource.collection_get()
        records = result['items']
        self.assertEqual(len(records), 1)

    def test_delete_on_collection_can_be_disabled_via_settings(self):
        with mock.patch.dict(self.resource.request.registry.settings,
                             [('cliquet.delete_collection_enabled', False)]):
            self.assertRaises(httpexceptions.HTTPMethodNotAllowed,
                              self.resource.collection_delete)


class IsolatedCollectionsTest(BaseTest):
    def setUp(self):
        super(IsolatedCollectionsTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})
        self.resource.record_id = self.stored['id']

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
