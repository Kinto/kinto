import mock
from pyramid import httpexceptions

from readinglist.errors import ERRORS
from readinglist.tests.resource import BaseTest


class GetTest(BaseTest):
    def test_get_record_returns_all_fields(self):
        record = self.db.create(self.resource, 'bob', {'field': 'value'})
        self.resource.request.matchdict['id'] = record['id']
        result = self.resource.get()
        self.assertIn(self.resource.id_field, result)
        self.assertIn(self.resource.modified_field, result)
        self.assertIn('field', result)


class PutTest(BaseTest):
    def setUp(self):
        super(PutTest, self).setUp()
        self.record = self.db.create(self.resource, 'bob', {'field': 'old'})
        self.resource.request.matchdict['id'] = self.record['id']

    def test_replace_record_returns_updated_fields(self):
        self.resource.request.validated = {'field': 'new'}

        result = self.resource.put()
        self.assertEqual(self.record['id'], result['id'])
        self.assertNotEqual(self.record['last_modified'],
                            result['last_modified'])
        self.assertNotEqual(self.record['field'], 'new')

    def test_cannot_replace_with_different_id(self):
        self.resource.request.validated = {'id': 'abc'}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.put)

    def test_last_modified_is_overwritten_on_replace(self):
        self.resource.request.validated = {'last_modified': 123}
        result = self.resource.put()
        self.assertNotEqual(result['last_modified'], 123)


class DeleteTest(BaseTest):
    def test_delete_record_returns_original_record(self):
        record = self.db.create(self.resource, 'bob', {'field': 'value'})
        self.resource.request.matchdict['id'] = record['id']
        result = self.resource.delete()
        self.assertDictEqual(result, record)


class PatchTest(BaseTest):
    def setUp(self):
        super(PatchTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})
        self.resource.request.matchdict['id'] = self.stored['id']
        self.resource.request.json = {'some': 'change'}
        self.resource.mapping.typ.unknown = 'preserve'
        self.result = self.resource.patch()

    def test_modify_record_updates_timestamp(self):
        before = self.stored['last_modified']
        after = self.result['last_modified']
        self.assertNotEquals(after, before)

    def test_patch_record_returns_updated_fields(self):
        self.assertEquals(self.stored['id'], self.result['id'])
        self.assertEquals(self.result['some'], 'change')

    def test_record_timestamp_is_not_updated_if_none_for_missing_field(self):
        self.resource.request.json = {'plop': None}
        result = self.resource.patch()
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_record_timestamp_is_not_updated_if_no_field_changed(self):
        self.resource.request.json = {'some': 'change'}
        result = self.resource.patch()
        self.assertEquals(self.result['last_modified'],
                          result['last_modified'])

    def test_collection_timestamp_is_not_updated_if_no_field_changed(self):
        self.resource.request.json = {'some': 'change'}
        self.resource.patch()
        # Reset
        BaseTest.setUp(self)
        self.resource.collection_get()
        last_modified = self.last_response.headers['Last-Modified']
        self.assertEquals(self.result['last_modified'], int(last_modified))

    def test_timestamp_is_not_updated_if_no_change_after_preprocessed(self):
        with mock.patch.object(self.resource, 'preprocess_record') as mocked:
            mocked.return_value = {'some': 'change'}

            self.resource.request.json = {'some': 'plop'}
            result = self.resource.patch()
            self.assertEquals(self.result['last_modified'],
                              result['last_modified'])


class UnknownRecordTest(BaseTest):
    def setUp(self):
        super(UnknownRecordTest, self).setUp()
        self.resource.request.matchdict['id'] = 'foo'

    def test_get_record_unknown_raises_404(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.get)

    def test_modify_record_unknown_raises_404(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.patch)

    def test_replace_record_unknown_creates_it(self):
        self.resource.put()
        self.db.get(self.resource, 'bob', 'foo')

    def test_delete_record_unknown_raises_404(self):
        self.assertRaises(httpexceptions.HTTPNotFound, self.resource.delete)


class ReadonlyFieldsTest(BaseTest):
    def setUp(self):
        super(ReadonlyFieldsTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})
        self.resource.request.matchdict['id'] = self.stored['id']

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
            'error': 'Invalid parameters'})

    def test_can_specify_readonly_fields_if_not_changed(self):
        self.resource.request.json = {
            'id': self.stored['id'],
            'last_modified': self.stored['last_modified']
        }
        self.resource.patch()  # not raising

    def test_cannot_modify_id(self):
        self.resource.request.json = {'id': 'change'}
        self.assertReadonlyError('id')

    def test_cannot_modify_last_modified(self):
        self.resource.request.json = {'last_modified': 123}
        self.assertReadonlyError('last_modified')
