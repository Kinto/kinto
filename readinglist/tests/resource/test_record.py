from pyramid import httpexceptions

from readinglist.errors import ERRORS
from readinglist.tests.resource import BaseTest


class GetTest(BaseTest):
    def test_get_record_returns_all_fields(self):
        record = self.db.create(self.resource, 'bob', {'field': 'value'})
        self.resource.request.matchdict['id'] = record['_id']
        result = self.resource.get()
        self.assertIn(self.resource.id_field, result)
        self.assertIn(self.resource.modified_field, result)
        self.assertIn('field', result)


class PutTest(BaseTest):
    def test_replace_record_returns_updated_fields(self):
        record = self.db.create(self.resource, 'bob', {'field': 'old'})

        self.resource.request.matchdict['id'] = record['_id']
        self.resource.request.validated = {'field': 'new'}

        result = self.resource.put()
        self.assertEqual(record['_id'], result['_id'])
        self.assertNotEqual(record['last_modified'], result['last_modified'])
        self.assertNotEqual(record['field'], 'new')


class DeleteTest(BaseTest):
    def test_delete_record_returns_original_record(self):
        record = self.db.create(self.resource, 'bob', {'field': 'value'})
        self.resource.request.matchdict['id'] = record['_id']
        result = self.resource.delete()
        self.assertDictEqual(result, record)


class PatchTest(BaseTest):
    def setUp(self):
        super(PatchTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})
        self.resource.request.matchdict['id'] = self.stored['_id']
        self.resource.request.json = {'some': 'change'}
        self.resource.mapping.typ.unknown = 'preserve'
        self.result = self.resource.patch()

    def test_modify_record_updates_timestamp(self):
        before = self.stored['last_modified']
        after = self.result['last_modified']
        self.assertNotEquals(after, before)

    def test_patch_record_returns_updated_fields(self):
        self.assertEquals(self.stored['_id'], self.result['_id'])
        self.assertEquals(self.result['some'], 'change')


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
        self.resource.request.matchdict['id'] = self.stored['_id']

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
            '_id': self.stored['_id'],
            'last_modified': self.stored['last_modified']
        }
        self.resource.patch()  # not raising

    def test_cannot_modify_id(self):
        self.resource.request.json = {'_id': 'change'}
        self.assertReadonlyError('_id')

    def test_cannot_modify_last_modified(self):
        self.resource.request.json = {'last_modified': 123}
        self.assertReadonlyError('last_modified')
