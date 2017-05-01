from pyramid import httpexceptions

from . import BaseTest


class ModelTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.record = self.model.create_record({'field': 'value'})

    def test_list_returns_all_records_in_data(self):
        result = self.resource.collection_get()
        records = result['data']
        self.assertEqual(len(records), 1)
        self.assertDictEqual(records[0], self.record)


class CreateTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.resource.request.validated['body'] = {'data': {'field': 'new'}}

    def test_new_records_are_linked_to_owner(self):
        resp = self.resource.collection_post()['data']
        record_id = resp['id']
        self.model.get_record(record_id)  # not raising

    def test_create_record_returns_at_least_id_and_last_modified(self):
        record = self.resource.collection_post()['data']
        self.assertIn(self.resource.model.id_field, record)
        self.assertIn(self.resource.model.modified_field, record)
        self.assertIn('field', record)


class DeleteModelTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.patch_known_field.start()
        self.model.create_record({'field': 'a'})
        self.model.create_record({'field': 'b'})

    def test_delete_on_list_removes_all_records(self):
        self.resource.collection_delete()
        result = self.resource.collection_get()
        records = result['data']
        self.assertEqual(len(records), 0)

    def test_delete_returns_deleted_version_of_records(self):
        result = self.resource.collection_delete()
        deleted = result['data'][0]
        self.assertIn('deleted', deleted)

    def test_delete_supports_collection_filters(self):
        self.resource.request.validated['querystring'] = {'field': 'a'}
        self.resource.collection_delete()
        self.resource.request.validated['querystring'] = {}
        result = self.resource.collection_get()
        records = result['data']
        self.assertEqual(len(records), 1)


class IsolatedModelsTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.resource.request.validated = {'header': {}, 'querystring': {}}
        self.stored = self.model.create_record({}, parent_id='bob')
        self.resource.record_id = self.stored['id']

    def get_request(self):
        request = super().get_request()
        request.prefixed_userid = 'basicauth:alice'
        return request

    def get_context(self):
        context = super().get_context()
        context.prefixed_userid = 'basicauth:alice'
        return context

    def test_list_is_filtered_by_user(self):
        resp = self.resource.collection_get()
        records = resp['data']
        self.assertEquals(len(records), 0)

    def test_update_record_of_another_user_will_create_it(self):
        self.resource.request.validated['body'] = {'data': {'some': 'record'}}
        self.resource.put()
        self.model.get_record(record_id=self.stored['id'],
                              parent_id='basicauth:alice')  # not raising

    def test_cannot_modify_record_of_other_user(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.patch)

    def test_cannot_delete_record_of_other_user(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.delete)
