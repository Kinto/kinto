import mock

import colander
from pyramid import httpexceptions

from cliquet.resource import ResourceSchema
from cliquet.errors import ERRORS
from cliquet.tests.resource import BaseTest


class GetTest(BaseTest):
    def test_get_record_returns_all_fields(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        result = self.resource.get()['data']
        self.assertIn(self.resource.model.id_field, result)
        self.assertIn(self.resource.model.modified_field, result)
        self.assertIn('field', result)

    def test_etag_is_provided(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        self.resource.get()
        self.assertIn('ETag', self.last_response.headers)

    def test_etag_contains_record_timestamp(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        # Create another one, bump collection timestamp.
        self.model.create_record({'field': 'value'})
        self.resource.get()
        expected = ('"%s"' % record['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])


class PutTest(BaseTest):
    def setUp(self):
        super(PutTest, self).setUp()
        self.record = self.model.create_record({'field': 'old'})
        self.resource.record_id = self.record['id']

    def test_etag_is_provided(self):
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.put()
        self.assertIn('ETag', self.last_response.headers)

    def test_etag_contains_record_new_timestamp(self):
        self.resource.request.validated = {'data': {'field': 'new'}}
        new = self.resource.put()['data']
        expected = ('"%s"' % new['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

    def test_returns_201_if_created(self):
        self.resource.record_id = self.resource.model.id_generator()
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.put()
        self.assertEqual(self.last_response.status_code, 201)

    def test_relies_on_collection_create(self):
        self.resource.record_id = self.resource.model.id_generator()
        self.resource.request.validated = {'data': {'field': 'new'}}
        with mock.patch.object(self.model, 'create_record') as patched:
            self.resource.put()
            self.assertEqual(patched.call_count, 1)

    def test_relies_on_collection_create_even_when_previously_deleted(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        self.resource.delete()['data']

        self.resource.request.validated = {'data': {'field': 'new'}}
        with mock.patch.object(self.model, 'create_record') as patched:
            self.resource.put()
            self.assertEqual(patched.call_count, 1)

    def test_replace_record_returns_updated_fields(self):
        self.resource.request.validated = {'data': {'field': 'new'}}
        result = self.resource.put()['data']
        self.assertEqual(self.record['id'], result['id'])
        self.assertNotEqual(self.record['last_modified'],
                            result['last_modified'])
        self.assertNotEqual(self.record['field'], 'new')

    def test_last_modified_is_kept_if_present(self):
        new_last_modified = self.record['last_modified'] + 20
        self.resource.request.validated = {'data': {
            'field': 'new',
            'last_modified': new_last_modified}
        }
        result = self.resource.put()['data']
        self.assertEqual(result['last_modified'], new_last_modified)

    def test_last_modified_is_dropped_if_same_as_previous(self):
        self.resource.request.validated = {'data': {
            'field': 'new',
            'last_modified': self.record['last_modified']}
        }
        result = self.resource.put()['data']
        self.assertGreater(result['last_modified'],
                           self.record['last_modified'])

    def test_last_modified_is_dropped_if_lesser_than_existing(self):
        new_last_modified = self.record['last_modified'] - 20
        self.resource.request.validated = {'data': {
            'field': 'new',
            'last_modified': new_last_modified}
        }
        result = self.resource.put()['data']
        self.assertNotEqual(result['last_modified'],
                            self.record['last_modified'])

    def test_cannot_replace_with_different_id(self):
        self.resource.request.validated = {'data': {'id': 'abc'}}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.put)

    def test_last_modified_is_overwritten_on_replace(self):
        self.resource.request.validated = {'data': {'last_modified': 123}}
        result = self.resource.put()['data']
        self.assertNotEqual(result['last_modified'], 123)

    def test_storage_is_not_used_if_context_provides_current_record(self):
        self.resource.context.current_record = {'id': 'hola'}
        self.resource.request.validated = {'data': {}}
        with mock.patch.object(self.resource.model, 'get_record') as get:
            self.resource.put()
            self.assertFalse(get.called)


class DeleteTest(BaseTest):
    def test_delete_record_returns_last_timestamp(self):
        record = {'field': 'value'}
        record = self.model.create_record(record).copy()
        self.resource.record_id = record['id']
        result = self.resource.delete()['data']
        self.assertNotEqual(result['last_modified'], record['last_modified'])

    def test_delete_record_returns_stripped_record(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        result = self.resource.delete()['data']
        self.assertEqual(result['id'], record['id'])
        self.assertNotIn('field', result)
        self.assertIn('last_modified', result)

    def test_delete_uses_last_modified_from_querystring(self):
        record = self.model.create_record({'field': 'value'})
        last_modified = record[self.model.modified_field] + 20
        self.resource.record_id = record['id']
        self.resource.request.GET = {
            'last_modified': '%s' % last_modified
        }

        result = self.resource.delete()['data']
        self.assertEqual(result[self.model.modified_field], last_modified)

        self.resource.request.GET = {'_since': '0', 'deleted': 'true'}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)
        retrieved = result['data'][0]
        self.assertEqual(retrieved[self.model.modified_field], last_modified)

    def test_delete_validates_the_last_modified_in_querystring(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        self.resource.request.GET = {'last_modified': 'abc'}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.delete)

    def test_delete_accepts_the_last_modified_between_quotes(self):
        record = self.model.create_record({'field': 'value'})
        last_modified = record[self.model.modified_field] + 20
        self.resource.record_id = record['id']
        self.resource.request.GET = {'last_modified': '"%s"' % last_modified}
        result = self.resource.delete()['data']
        self.assertEqual(result[self.model.modified_field], last_modified)

    def test_delete_ignores_last_modified_if_equal(self):
        record = self.model.create_record({'field': 'value'})
        last_modified = record[self.model.modified_field]
        self.resource.record_id = record['id']
        self.resource.request.GET = {'last_modified': '%s' % last_modified}
        result = self.resource.delete()['data']
        self.assertGreater(result[self.model.modified_field], last_modified)

    def test_delete_ignores_last_modified_if_less(self):
        record = self.model.create_record({'field': 'value'})
        last_modified = record[self.model.modified_field] - 20
        self.resource.record_id = record['id']
        self.resource.request.GET = {'last_modified': '%s' % last_modified}
        result = self.resource.delete()['data']
        self.assertGreater(result[self.model.modified_field], last_modified)


class PatchTest(BaseTest):
    def setUp(self):
        super(PatchTest, self).setUp()
        self.stored = self.model.create_record({})
        self.resource.record_id = self.stored['id']
        self.resource.request.json = {'data': {'position': 10}}
        schema = ResourceSchema()
        schema.add(colander.SchemaNode(colander.Boolean(), name='unread',
                                       missing=colander.drop))
        schema.add(colander.SchemaNode(colander.Int(), name='position',
                                       missing=colander.drop))
        self.resource.mapping = schema
        self.result = self.resource.patch()['data']

    def test_etag_is_provided(self):
        self.assertIn('ETag', self.last_response.headers)

    def test_etag_contains_record_new_timestamp(self):
        expected = ('"%s"' % self.result['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

    def test_etag_contains_old_timestamp_if_no_field_changed(self):
        self.resource.request.json = {'data': {'position': 10}}
        self.resource.patch()['data']
        expected = ('"%s"' % self.result['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

    def test_modify_record_updates_timestamp(self):
        before = self.stored['last_modified']
        after = self.result['last_modified']
        self.assertNotEquals(after, before)

    def test_patch_record_returns_updated_fields(self):
        self.assertEquals(self.stored['id'], self.result['id'])
        self.assertEquals(self.result['position'], 10)

    def test_record_timestamp_is_not_updated_if_none_for_missing_field(self):
        self.resource.request.json = {'data': {'polo': None}}
        result = self.resource.patch()['data']
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_record_timestamp_is_not_updated_if_no_field_changed(self):
        self.resource.request.json = {'data': {'position': 10}}
        result = self.resource.patch()['data']
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_collection_timestamp_is_not_updated_if_no_field_changed(self):
        self.resource.request.json = {'data': {'position': 10}}
        self.resource.patch()
        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.resource.collection_get()['data']
        last_modified = int(self.last_response.headers['ETag'][1:-1])
        self.assertEquals(self.result['last_modified'], last_modified)

    def test_timestamp_is_not_updated_if_no_change_after_preprocessed(self):
        with mock.patch.object(self.resource, 'process_record') as mocked:
            mocked.return_value = self.result
            self.resource.request.json = {'data': {'position': 20}}
            result = self.resource.patch()['data']
            self.assertEquals(self.result['last_modified'],
                              result['last_modified'])

    def test_returns_changed_fields_among_provided_if_behaviour_is_diff(self):
        self.resource.request.json = {'data': {'unread': True, 'position': 15}}
        self.resource.request.headers['Response-Behavior'] = 'diff'
        with mock.patch.object(self.resource.model, 'update_record',
                               return_value={'unread': True, 'position': 0}):
            result = self.resource.patch()['data']
        self.assertDictEqual(result, {'position': 0})

    def test_returns_changed_fields_if_behaviour_is_light(self):
        self.resource.request.json = {'data': {'unread': True, 'position': 15}}
        self.resource.request.headers['Response-Behavior'] = 'light'
        with mock.patch.object(self.resource.model, 'update_record',
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
        self.model.get_record(self.unknown_id)

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
        self.stored = self.model.create_record({'age': 32})
        self.resource.mapping.Options.readonly_fields = ('age',)
        self.resource.record_id = self.stored['id']

    def assertReadonlyError(self, field):
        error = None
        try:
            self.resource.patch()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.INVALID_PARAMETERS.value,
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
