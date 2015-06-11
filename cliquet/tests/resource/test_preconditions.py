from pyramid import httpexceptions

from cliquet.errors import ERRORS
from cliquet.resource import BaseResource
from cliquet.tests.resource import BaseTest


class NotModifiedTest(BaseTest):
    def setUp(self):
        super(NotModifiedTest, self).setUp()
        self.stored = self.collection.create_record({})

        self.resource = BaseResource(self.get_request())
        self.resource.collection_get()
        current = self.last_response.headers['ETag']
        self.resource.request.headers['If-None-Match'] = current

    def test_collection_returns_304_if_no_change_meanwhile(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertEqual(error.code, 304)
        self.assertIsNotNone(error.headers.get('ETag'))
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_single_record_returns_304_if_no_change_meanwhile(self):
        self.resource.record_id = self.stored['id']
        try:
            self.resource.get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertEqual(error.code, 304)
        self.assertIsNotNone(error.headers.get('ETag'))
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_single_record_last_modified_is_returned(self):
        self.resource.timestamp = 0
        self.resource.record_id = self.stored['id']
        try:
            self.resource.get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertNotIn('1970', error.headers['Last-Modified'])

    def test_if_none_match_empty_raises_invalid(self):
        self.resource.request.headers['If-None-Match'] = '""'.encode('utf-8')
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_none_match_without_quotes_raises_invalid(self):
        self.resource.request.headers['If-None-Match'] = '1234'.encode('utf-8')
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_none_match_not_integer_raises_invalid(self):
        self.resource.request.headers['If-None-Match'] = '"ab"'.encode('utf-8')
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)


class ModifiedMeanwhileTest(BaseTest):
    def setUp(self):
        super(ModifiedMeanwhileTest, self).setUp()
        self.stored = self.collection.create_record({})
        self.resource.collection_get()
        current = self.last_response.headers['ETag'][1:-1].decode('utf-8')
        previous = int(current) - 10
        if_match = ('"%s"' % previous).encode('utf-8')
        self.resource.request.headers['If-Match'] = if_match

    def test_preconditions_errors_are_json_formatted(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.MODIFIED_MEANWHILE,
            'message': 'Resource was modified meanwhile',
            'code': 412,
            'error': 'Precondition Failed'})

    def test_collection_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_get)

    def test_412_on_collection_has_last_modified_timestamp(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertIsNotNone(error.headers.get('ETag'))
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_single_record_returns_412_if_changed_meanwhile(self):
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.get)

    def test_412_on_single_record_has_last_modified_timestamp(self):
        self.resource.record_id = self.stored['id']
        try:
            self.resource.get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertIsNotNone(error.headers.get('ETag'))
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_create_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_post)

    def test_put_returns_412_if_changed_meanwhile(self):
        self.resource.record_id = self.stored['id']
        self.collection.delete_record(self.stored)
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.put)

    def test_put_returns_last_modified_if_changed_meanwhile(self):
        self.resource.timestamp = 0
        self.resource.record_id = self.stored['id']
        try:
            self.resource.put()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertNotIn('1970', error.headers['Last-Modified'])

    def test_put_returns_412_if_deleted_meanwhile(self):
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.put)

    def test_if_none_match_star_fails_if_record_exists(self):
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'.encode('utf-8')
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.put)
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.record_id = self.resource.collection.id_generator()
        self.resource.put()  # not raising.

    def test_patch_returns_412_if_changed_meanwhile(self):
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.patch)

    def test_patch_returns_last_modified_if_changed_meanwhile(self):
        self.resource.timestamp = 0
        self.resource.record_id = self.stored['id']
        try:
            self.resource.patch()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertNotIn('1970', error.headers['Last-Modified'])

    def test_delete_returns_412_if_changed_meanwhile(self):
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.delete)

    def test_delete_all_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_delete)

    def test_if_match_without_quotes_raises_invalid(self):
        self.resource.request.headers['If-Match'] = '123456'.encode('utf-8')
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_match_empty_raises_invalid(self):
        self.resource.request.headers['If-Match'] = '""'.encode('utf-8')
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_match_not_integer_raises_invalid(self):
        self.resource.request.headers['If-Match'] = '"abc"'.encode('utf-8')
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)
