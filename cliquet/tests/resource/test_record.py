import mock
from pyramid import httpexceptions

from cliquet.resource import BaseResource
from cliquet.errors import ERRORS
from cliquet.tests.resource import BaseTest


class GetTest(BaseTest):
    def test_get_record_returns_all_fields(self):
        record = self.collection.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        result = self.resource.get()['data']
        self.assertIn(self.resource.collection.id_field, result)
        self.assertIn(self.resource.collection.modified_field, result)
        self.assertIn('field', result)


class PutTest(BaseTest):
    def setUp(self):
        super(PutTest, self).setUp()
        self.record = self.collection.create_record({'field': 'old'})
        self.resource.record_id = self.record['id']

    def test_returns_201_if_created(self):
        self.resource.record_id = self.resource.collection.id_generator()
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.put()
        self.assertEqual(self.last_response.status_code, 201)

    def test_replace_record_returns_updated_fields(self):
        self.resource.request.validated = {'data': {'field': 'new'}}
        result = self.resource.put()['data']
        self.assertEqual(self.record['id'], result['id'])
        self.assertNotEqual(self.record['last_modified'],
                            result['last_modified'])
        self.assertNotEqual(self.record['field'], 'new')

    def test_cannot_replace_with_different_id(self):
        self.resource.request.validated = {'data': {'id': 'abc'}}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.put)

    def test_last_modified_is_overwritten_on_replace(self):
        self.resource.request.validated = {'data': {'last_modified': 123}}
        result = self.resource.put()['data']
        self.assertNotEqual(result['last_modified'], 123)


class DeleteTest(BaseTest):
    def test_delete_record_returns_last_timestamp(self):
        record = {'field': 'value'}
        record = self.collection.create_record(record).copy()
        self.resource.record_id = record['id']
        result = self.resource.delete()['data']
        self.assertNotEqual(result['last_modified'], record['last_modified'])

    def test_delete_record_returns_stripped_record(self):
        record = self.collection.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        result = self.resource.delete()['data']
        self.assertEqual(result['id'], record['id'])
        self.assertNotIn('field', result)
        self.assertIn('last_modified', result)


class PatchTest(BaseTest):
    def setUp(self):
        super(PatchTest, self).setUp()
        self.stored = self.collection.create_record({})
        self.resource.record_id = self.stored['id']
        self.resource.request.json = {'data': {'some': 'change'}}
        self.resource.mapping.typ.unknown = 'preserve'
        self.result = self.resource.patch()['data']

    def test_modify_record_updates_timestamp(self):
        before = self.stored['last_modified']
        after = self.result['last_modified']
        self.assertNotEquals(after, before)

    def test_patch_record_returns_updated_fields(self):
        self.assertEquals(self.stored['id'], self.result['id'])
        self.assertEquals(self.result['some'], 'change')

    def test_record_timestamp_is_not_updated_if_none_for_missing_field(self):
        self.resource.request.json = {'data': {'plop': None}}
        result = self.resource.patch()['data']
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_record_timestamp_is_not_updated_if_no_field_changed(self):
        self.resource.request.json = {'data': {'some': 'change'}}
        result = self.resource.patch()['data']
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_collection_timestamp_is_not_updated_if_no_field_changed(self):
        self.resource.request.json = {'data': {'some': 'change'}}
        self.resource.patch()
        self.resource = BaseResource(self.get_request())
        self.resource.collection_get()['data']
        last_modified = int(self.last_response.headers['ETag'][1:-1])
        self.assertEquals(self.result['last_modified'], last_modified)

    def test_timestamp_is_not_updated_if_no_change_after_preprocessed(self):
        with mock.patch.object(self.resource, 'process_record') as mocked:
            mocked.return_value = self.result
            self.resource.request.json = {'data': {'some': 'plop'}}
            result = self.resource.patch()['data']
            self.assertEquals(self.result['last_modified'],
                              result['last_modified'])

    def test_returns_changed_fields_among_provided_if_behaviour_is_diff(self):
        self.resource.request.json = {'data': {'unread': True, 'position': 10}}
        self.resource.request.headers['Response-Behavior'] = 'diff'
        with mock.patch.object(self.resource.collection, 'update_record',
                               return_value={'unread': True, 'position': 0}):
            result = self.resource.patch()['data']
        self.assertDictEqual(result, {'position': 0})

    def test_returns_changed_fields_if_behaviour_is_light(self):
        self.resource.request.json = {'data': {'unread': True, 'position': 10}}
        self.resource.request.headers['Response-Behavior'] = 'light'
        with mock.patch.object(self.resource.collection, 'update_record',
                               return_value={'unread': True, 'position': 0}):
            result = self.resource.patch()['data']
        self.assertDictEqual(result, {'unread': True, 'position': 0})


class UnknownRecordTest(BaseTest):
    def setUp(self):
        super(UnknownRecordTest, self).setUp()
        self.unknown_id = '1cea99eb-5e3d-44ad-a53a-2fb68473b538'
        self.resource.record_id = self.unknown_id
        self.resource.request.validated = {'data': {'field': 'new'}}

    def test_get_record_unknown_raises_404(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.get)

    def test_modify_record_unknown_raises_404(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.patch)

    def test_replace_record_unknown_creates_it(self):
        self.resource.put()
        self.collection.get_record(self.unknown_id)

    def test_delete_record_unknown_raises_404(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.delete)


class InvalidIdTest(BaseTest):
    def setUp(self):
        super(InvalidIdTest, self).setUp()
        self.resource.record_id = 'a*b'

    def test_get_with_invalid_id_raises_400(self):
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.get)

    def test_patch_with_invalid_id_raises_400(self):
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.patch)

    def test_put_with_invalid_id_raises_400(self):
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.put)

    def test_delete_with_invalid_id_raises_400(self):
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.delete)


class ReadonlyFieldsTest(BaseTest):
    def setUp(self):
        super(ReadonlyFieldsTest, self).setUp()
        self.stored = self.collection.create_record({'age': 32})
        self.resource.mapping.Options.readonly_fields = ('age',)
        self.resource.record_id = self.stored['id']

    def assertReadonlyError(self, field):
        error = None
        try:
            self.resource.patch()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': 'Cannot modify {0}'.format(field),
            'code': 400,
            'error': 'Invalid parameters',
            'details': [{'description': 'Cannot modify age',
                         'location': 'body',
                         'name': 'age'}]})

    def test_can_specify_readonly_fields_if_not_changed(self):
        self.resource.request.json = {'data': {'age': self.stored['age']}}
        self.resource.patch()  # not raising

    def test_cannot_modify_readonly_field(self):
        self.resource.request.json = {'data': {'age': 16}}
        self.assertReadonlyError('age')
