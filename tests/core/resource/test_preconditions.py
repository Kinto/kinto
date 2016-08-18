from pyramid import httpexceptions

from kinto.core.errors import ERRORS
from kinto.tests.core.resource import BaseTest


class NotModifiedTest(BaseTest):
    def setUp(self):
        super(NotModifiedTest, self).setUp()
        self.stored = self.model.create_record({})

        self.resource = self.resource_class(request=self.get_request(),
                                            context=self.get_context())
        self.resource.collection_get()
        current = self.last_response.headers['ETag']
        self.resource.request.headers['If-None-Match'] = current

    def test_collection_returns_200_if_change_meanwhile(self):
        self.resource.request.headers['If-None-Match'] = '"42"'
        self.resource.collection_get()  # Not raising.

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
        self.resource.request.headers['If-None-Match'] = '""'
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_none_match_without_quotes_raises_invalid(self):
        self.resource.request.headers['If-None-Match'] = '1234'
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_none_match_not_integer_raises_invalid(self):
        self.resource.request.headers['If-None-Match'] = '"ab"'
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)


class ModifiedMeanwhileTest(BaseTest):
    def setUp(self):
        super(ModifiedMeanwhileTest, self).setUp()
        self.stored = self.model.create_record({})

        self.resource.collection_get()
        current = self.last_response.headers['ETag'][1:-1]
        previous = int(current) - 10
        if_match = ('"%s"' % previous)
        self.resource.request.headers['If-Match'] = if_match

    def test_preconditions_errors_are_json_formatted(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertEqual(error.json, {
            'errno': ERRORS.MODIFIED_MEANWHILE.value,
            'details': {},
            'message': 'Resource was modified meanwhile',
            'code': 412,
            'error': 'Precondition Failed'})

    def test_collection_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_get)

    def test_412_errors_on_collection_do_not_provide_existing_record(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertNotIn('existing', error.json['details'])

    def test_412_on_collection_has_last_modified_timestamp(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertIsNotNone(error.headers.get('ETag'))
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_412_errors_on_record_provide_existing_data(self):
        self.resource.record_id = self.stored['id']
        try:
            self.resource.put()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertEqual(error.json['details']['existing'],
                         self.stored)

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
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_post)

    def test_put_returns_412_if_changed_meanwhile(self):
        self.resource.record_id = self.stored['id']
        self.model.delete_record(self.stored)
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.put)

    def test_put_returns_412_if_changed_and_none_match_present(self):
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.request.headers['If-None-Match'] = '"42"'
        self.resource.record_id = self.stored['id']
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

    def test_put_if_none_match_star_fails_if_record_exists(self):
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.put)

    def test_get_if_none_match_star_fails_if_record_exists(self):
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'
        self.resource.record_id = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.get)

    def test_put_if_none_match_star_succeeds_if_record_does_not_exist(self):
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.record_id = self.resource.model.id_generator()
        self.resource.put()  # not raising.

    def test_put_if_none_match_star_succeeds_if_tombstone_exists(self):
        self.model.delete_record(self.stored)
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'
        self.resource.request.validated = {'data': {'field': 'new'}}
        self.resource.record_id = self.stored['id']
        self.resource.put()  # not raising.

    def test_post_if_none_match_star_fails_if_record_exists(self):
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'
        self.resource.request.json = self.resource.request.validated = {
            'data': {
                'id': self.stored['id'],
                'field': 'new'}}
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_post)

    def test_post_if_none_match_star_succeeds_if_record_does_not_exist(self):
        self.resource.request.headers.pop('If-Match')
        self.resource.request.headers['If-None-Match'] = '*'
        self.resource.request.validated = {
            'data': {
                'id': self.resource.model.id_generator(),
                'field': 'new'}}
        self.resource.collection_post()  # not raising.

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
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.request.headers['If-Match'] = '123456'
            self.resource.collection_get()
        expected_message = ('headers: Invalid value for If-Match. The value '
                            'should be integer between double quotes.')
        self.assertEquals(cm.exception.json['message'], expected_message)

    def test_if_match_empty_raises_invalid(self):
        self.resource.request.headers['If-Match'] = '""'
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)

    def test_if_match_not_integer_raises_invalid(self):
        self.resource.request.headers['If-Match'] = '"abc"'
        self.assertRaises(httpexceptions.HTTPBadRequest,
                          self.resource.collection_get)
