import mock

import colander
from pyramid import httpexceptions

from kinto.core.resource import ResourceSchema
from kinto.core.errors import ERRORS

from . import BaseTest


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
        expected = '"{}"'.format(record['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])


class PutTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.record = self.model.create_record({'field': 'old'})
        self.resource.record_id = self.record['id']

    def test_etag_is_provided(self):
        self.validated['body'] = {'data': {'field': 'new'}}
        self.resource.put()
        self.assertIn('ETag', self.last_response.headers)

    def test_etag_contains_record_new_timestamp(self):
        self.validated['body'] = {'data': {'field': 'new'}}
        new = self.resource.put()['data']
        expected = '"{}"'.format(new['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

    def test_returns_201_if_created(self):
        self.resource.record_id = self.resource.model.id_generator()
        self.validated['body'] = {'data': {'field': 'new'}}
        self.resource.put()
        self.assertEqual(self.last_response.status_code, 201)

    def test_relies_on_collection_create(self):
        self.resource.record_id = self.resource.model.id_generator()
        self.validated['body'] = {'data': {'field': 'new'}}
        with mock.patch.object(self.model, 'create_record') as patched:
            self.resource.put()
            self.assertEqual(patched.call_count, 1)

    def test_relies_on_collection_create_even_when_previously_deleted(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        self.resource.delete()['data']

        self.validated['body'] = {'data': {'field': 'new'}}
        with mock.patch.object(self.model, 'create_record') as patched:
            self.resource.put()
            self.assertEqual(patched.call_count, 1)

    def test_replace_record_returns_updated_fields(self):
        self.validated['body'] = {'data': {'field': 'new'}}
        result = self.resource.put()['data']
        self.assertEqual(self.record['id'], result['id'])
        self.assertNotEqual(self.record['last_modified'],
                            result['last_modified'])
        self.assertNotEqual(self.record['field'], 'new')

    def test_last_modified_is_kept_if_present(self):
        new_last_modified = self.record['last_modified'] + 20
        self.validated['body'] = {'data': {
            'field': 'new',
            'last_modified': new_last_modified}
        }
        result = self.resource.put()['data']
        self.assertEqual(result['last_modified'], new_last_modified)

    def test_last_modified_is_dropped_if_same_as_previous(self):
        self.validated['body'] = {'data': {
            'field': 'new',
            'last_modified': self.record['last_modified']}
        }
        result = self.resource.put()['data']
        self.assertGreater(result['last_modified'],
                           self.record['last_modified'])

    def test_last_modified_is_dropped_if_lesser_than_existing(self):
        new_last_modified = self.record['last_modified'] - 20
        self.validated['body'] = {'data': {
            'field': 'new',
            'last_modified': new_last_modified}
        }
        result = self.resource.put()['data']
        self.assertNotEqual(result['last_modified'],
                            self.record['last_modified'])

    def test_cannot_replace_with_different_id(self):
        self.validated['body'] = {'data': {'id': 'abc'}}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.put)

    def test_last_modified_is_overwritten_on_replace(self):
        self.validated['body'] = {'data': {'last_modified': 123}}
        result = self.resource.put()['data']
        self.assertNotEqual(result['last_modified'], 123)

    def test_storage_is_not_used_if_context_provides_current_record(self):
        self.resource.context.current_record = {'id': 'hola'}
        self.validated['body'] = {'data': {}}
        with mock.patch.object(self.resource.model, 'get_record') as get:
            self.resource.put()
            self.assertFalse(get.called)

    def test_put_over_tombstone_create_new_record(self):
        self.resource.delete()
        result = self.resource.put()
        self.assertNotIn("old", result)
        self.assertNotIn("deleted", result)


class DeleteTest(BaseTest):
    def test_delete_record_returns_last_timestamp(self):
        record = {'field': 'value'}
        record = {**self.model.create_record(record)}
        self.resource.record_id = record['id']
        result = self.resource.delete()['data']
        self.assertNotEqual(result['last_modified'], record['last_modified'])

    def test_etag_is_provided(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        self.resource.delete()
        self.assertIn('ETag', self.last_response.headers)

    def test_etag_contains_deleted_timestamp(self):
        record = self.model.create_record({'field': 'value'})
        self.resource.record_id = record['id']
        deleted = self.resource.delete()
        expected = '"{}"'.format(deleted['data']['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

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
        self.validated['querystring']['last_modified'] = last_modified
        result = self.resource.delete()['data']
        self.validated = self.validated
        self.assertEqual(result[self.model.modified_field], last_modified)
        self.validated['querystring'] = {
            '_since': 0, 'deleted': True}
        result = self.resource.collection_get()
        self.assertEqual(len(result['data']), 1)
        retrieved = result['data'][0]
        self.assertEqual(retrieved[self.model.modified_field], last_modified)

    def test_delete_ignores_last_modified_if_equal(self):
        record = self.model.create_record({'field': 'value'})
        last_modified = record[self.model.modified_field]
        self.resource.record_id = record['id']
        self.validated['querystring']['last_modified'] = last_modified
        result = self.resource.delete()['data']
        self.assertGreater(result[self.model.modified_field], last_modified)

    def test_delete_ignores_last_modified_if_less(self):
        record = self.model.create_record({'field': 'value'})
        last_modified = record[self.model.modified_field] - 20
        self.resource.record_id = record['id']
        self.validated['querystring']['last_modified'] = last_modified
        result = self.resource.delete()['data']
        self.assertGreater(result[self.model.modified_field], last_modified)


class PatchTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.stored = self.model.create_record({})
        self.resource.record_id = self.stored['id']
        self.validated['body'] = {'data': {'position': 10}}

        class ArticleSchema(ResourceSchema):
            unread = colander.SchemaNode(colander.Boolean(), missing=colander.drop)
            position = colander.SchemaNode(colander.Int(), missing=colander.drop)

        self.resource.schema = ArticleSchema

        self.result = self.resource.patch()['data']

    def test_etag_is_provided(self):
        self.assertIn('ETag', self.last_response.headers)

    def test_etag_contains_record_new_timestamp(self):
        expected = '"{}"'.format(self.result['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

    def test_etag_contains_old_timestamp_if_no_field_changed(self):
        self.validated['body'] = {'data': {'position': 10}}
        self.resource.patch()['data']
        expected = '"{}"'.format(self.result['last_modified'])
        self.assertEqual(expected, self.last_response.headers['ETag'])

    def test_modify_record_updates_timestamp(self):
        before = self.stored['last_modified']
        after = self.result['last_modified']
        self.assertNotEquals(after, before)

    def test_patch_record_returns_updated_fields(self):
        self.assertEquals(self.stored['id'], self.result['id'])
        self.assertEquals(self.result['position'], 10)

    def test_record_timestamp_is_not_updated_if_none_for_missing_field(self):
        self.validated['body'] = {'data': {'polo': None}}
        result = self.resource.patch()['data']
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_record_timestamp_is_not_updated_if_no_field_changed(self):
        self.validated['body'] = {'data': {'position': 10}}
        result = self.resource.patch()['data']
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_collection_timestamp_is_not_updated_if_no_field_changed(self):
        self.validated['body'] = {'data': {'position': 10}}
        self.resource.patch()
        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.resource.request.validated = self.validated
        self.resource.collection_get()['data']
        last_modified = int(self.last_response.headers['ETag'][1:-1])
        self.assertEquals(self.result['last_modified'], last_modified)

    def test_timestamp_is_not_updated_if_no_change_after_preprocessed(self):
        with mock.patch.object(self.resource, 'process_record') as mocked:
            mocked.return_value = self.result
            self.validated['body'] = {'data': {'position': 20}}
            result = self.resource.patch()['data']
            self.assertEquals(self.result['last_modified'],
                              result['last_modified'])

    def test_returns_changed_fields_among_provided_if_behaviour_is_diff(self):
        self.validated['body'] = {'data': {'unread': True, 'position': 15}}
        self.validated['header'] = {
            'Response-Behavior': 'diff'
        }
        with mock.patch.object(self.resource.model, 'update_record',
                               return_value={'unread': True, 'position': 0}):
            result = self.resource.patch()['data']
        self.assertDictEqual(result, {'position': 0})

    def test_returns_changed_fields_if_behaviour_is_light(self):
        self.validated['body'] = {'data': {'unread': True, 'position': 15}}
        self.validated['header'] = {
            'Response-Behavior': 'light'
        }
        with mock.patch.object(self.resource.model, 'update_record',
                               return_value={'unread': True, 'position': 0}):
            result = self.resource.patch()['data']
        self.assertDictEqual(result, {'unread': True, 'position': 0})


class MergePatchTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.stored = self.model.create_record({})
        self.resource.record_id = self.stored['id']
        self.headers = self.resource.request.headers
        self.headers['Content-Type'] = 'application/merge-patch+json'

        class ArticleSchema(ResourceSchema):
            unread = colander.SchemaNode(colander.Boolean(), missing=colander.drop)
            position = colander.SchemaNode(colander.Int(), missing=colander.drop)

        self.resource.schema = ArticleSchema

    def test_merge_patch_updates_attributes_recursively(self):
        self.validated['body'] = {'data': {'a': {'b': 'bbb',
                                                 'c': 'ccc'}}}
        self.resource.patch()
        self.validated['body'] = {'data': {'a': {'b': 'aaa',
                                                 'c': None}}}
        result = self.resource.patch()['data']
        self.assertEqual(result['a']['b'], 'aaa')

    def test_merge_patch_removes_attribute_if_none(self):
        self.validated['body'] = {'data': {'field': 'aaa'}}
        self.resource.patch()
        self.validated['body'] = {'data': {'field': None}}
        result = self.resource.patch()['data']
        self.assertNotIn('field', result)
        result = self.resource.get()['data']
        self.assertNotIn('field', result)

    def test_merge_patch_removes_attributes_recursively_if_none(self):
        self.validated['body'] = {'data': {'a': {'b': 'aaa'}}}
        self.resource.patch()
        self.validated['body'] = {'data': {'a': {'b': None}}}
        result = self.resource.patch()['data']
        self.assertIn('a', result)
        self.assertNotIn('b', result['a'])
        self.validated['body'] = {'data': {'aa': {'bb': {'cc': None}}}}
        result = self.resource.patch()['data']
        self.assertIn('aa', result)
        self.assertIn('bb', result['aa'])
        self.assertNotIn('cc', result['aa']['bb'])

    def test_merge_patch_doesnt_remove_attribute_if_false(self):
        self.validated['body'] = {'data': {'field': 0}}
        result = self.resource.patch()['data']
        self.assertIn('field', result)
        self.validated['body'] = {'data': {'field': False}}
        result = self.resource.patch()['data']
        self.assertIn('field', result)
        self.validated['body'] = {'data': {'field': {}}}
        result = self.resource.patch()['data']
        self.assertIn('field', result)

    def test_patch_doesnt_remove_attribute_if_not_merge_header(self):
        self.headers['Content-Type'] = 'application/json'
        self.validated['body'] = {'data': {'field': 'aaa'}}
        self.resource.patch()
        self.validated['body'] = {'data': {'field': None}}
        result = self.resource.patch()['data']
        self.assertIn('field', result)
        result = self.resource.get()['data']
        self.assertIn('field', result)

    def test_merge_patch_doesnt_remove_previously_inserted_nones(self):
        self.headers['Content-Type'] = 'application/json'
        self.validated['body'] = {'data': {'field': 'aaa'}}
        result = self.resource.patch()['data']
        self.validated['body'] = {'data': {'field': None}}
        result = self.resource.patch()['data']
        self.assertIn('field', result)
        self.headers['Content-Type'] = 'application/merge-patch+json'
        self.validated['body'] = {'data': {'position': 10}}
        result = self.resource.patch()['data']
        self.assertIn('field', result)


class JsonPatchTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.stored = self.model.create_record({})
        self.resource.record_id = self.stored['id']
        self.validated['body'] = {'data': {'a': 'aaa', 'b': ['bb', 'bbb'], 'd': []}}
        self.resource.schema = ResourceSchema
        self.result = self.resource.patch()['data']
        header = self.resource.request.headers
        header['Content-Type'] = 'application/json-patch+json'
        self.resource._is_json_patch = True

    def test_json_patch_add(self):
        self.validated['body'] = [
            {'op': 'add', 'path': '/data/c', 'value': 'ccc'},
            {'op': 'add', 'path': '/data/b/1', 'value': 'ddd'},
            {'op': 'add', 'path': '/data/b/-', 'value': 'eee'},
        ]
        result = self.resource.patch()['data']
        self.assertEqual(result['c'], 'ccc')
        self.assertEqual(result['b'][0], 'bb')
        self.assertEqual(result['b'][1], 'ddd')
        self.assertEqual(result['b'][2], 'bbb')
        self.assertEqual(result['b'][3], 'eee')
        self.assertEqual(len(result['b']), 4)

    def test_json_patch_remove(self):
        self.validated['body'] = [
            {'op': 'remove', 'path': '/data/a'},
            {'op': 'remove', 'path': '/data/b/0'},
        ]
        result = self.resource.patch()['data']
        self.assertNotIn('a', result)
        self.assertEqual(len(result['b']), 1)
        self.assertEqual(result['b'][0], 'bbb')

    def test_json_patch_test_success(self):
        self.validated['body'] = [
            {'op': 'test', 'path': '/data/a', 'value': 'aaa'},
        ]
        self.resource.patch()['data']

    def test_json_patch_test_failure(self):
        self.validated['body'] = [
            {'op': 'test', 'path': '/data/a', 'value': 'bbb'},
        ]
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.patch)

    def test_json_patch_move(self):
        self.validated['body'] = [
            {'op': 'move', 'from': '/data/a', 'path': '/data/c'},
            {'op': 'move', 'from': '/data/b/1', 'path': '/data/d/0'},
            {'op': 'move', 'from': '/data/b/0', 'path': '/data/e'},
        ]
        result = self.resource.patch()['data']
        self.assertNotIn('a', result)
        self.assertEqual(result['c'], 'aaa')
        self.assertEqual(len(result['b']), 0)
        self.assertEqual(result['d'][0], 'bbb')
        self.assertEqual(result['e'], 'bb')

    def test_json_patch_copy(self):
        self.validated['body'] = [
            {'op': 'copy', 'from': '/data/a', 'path': '/data/c'},
            {'op': 'copy', 'from': '/data/b/1', 'path': '/data/d/0'},
            {'op': 'copy', 'from': '/data/d/0', 'path': '/data/e'},
        ]
        result = self.resource.patch()['data']
        self.assertEqual(result['a'], 'aaa')
        self.assertEqual(result['c'], 'aaa')
        self.assertEqual(len(result['b']), 2)
        self.assertEqual(result['d'][0], 'bbb')
        self.assertEqual(result['e'], 'bbb')

    def test_json_patch_replace(self):
        self.validated['body'] = [
            {'op': 'replace', 'path': '/data/a', 'value': 'bbb'},
            {'op': 'replace', 'path': '/data/b/0', 'value': 'aaa'},
        ]
        result = self.resource.patch()['data']
        self.assertEqual(result['a'], 'bbb')
        self.assertEqual(result['b'][0], 'aaa')

    def test_json_patch_raises_400_on_invalid_path(self):
        self.validated['body'] = [
            {'op': 'remove', 'path': '/data/f'},
        ]
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.patch)
        self.validated['body'] = [
            {'op': 'move', 'from': '/data/f', 'path': '/data/what'},
        ]
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.patch)
        self.validated['body'] = [
            {'op': 'copy', 'from': '/data/what', 'path': '/data/f'},
        ]
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.patch)
        self.validated['body'] = [
            {'op': 'replace', 'path': '/data/c', 'value': 'ccc'},
        ]
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.patch)

    def test_json_patch_format_not_accepted_without_header(self):
        header = self.resource.request.headers
        header['Content-Type'] = 'application/json'
        self.resource._is_json_patch = False
        self.validated['body'] = [
            {'op': 'add', 'from': '/data/a', 'value': 'aaa'},
        ]
        self.assertRaises(AttributeError, self.resource.patch)


class UnknownRecordTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.unknown_id = '1cea99eb-5e3d-44ad-a53a-2fb68473b538'
        self.resource.record_id = self.unknown_id
        self.validated['body'] = {'data': {'field': 'new'}}

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
        super().setUp()
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
        super().setUp()
        self.stored = self.model.create_record({'age': 32})
        self.resource.schema.Options.readonly_fields = ('age',)
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
        self.validated['body'] = {'data': {'age': self.stored['age']}}
        self.resource.patch()  # not raising

    def test_cannot_modify_readonly_field(self):
        self.validated['body'] = {'data': {'age': 16}}
        self.assertReadonlyError('age')
