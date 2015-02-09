import six
from pyramid import httpexceptions

from readinglist.errors import ERRORS
from readinglist.resource import BaseResource
from readinglist.tests.resource import BaseTest


class NotModifiedTest(BaseTest):
    def setUp(self):
        super(NotModifiedTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})

        self.resource = BaseResource(self.get_request())
        self.resource.collection_get()
        current = self.last_response.headers['Last-Modified']
        self.resource.request.headers['If-Modified-Since'] = current

    def test_collection_returns_304_if_no_change_meanwhile(self):
        try:
            self.resource.collection_get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertEqual(error.code, 304)
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_single_record_returns_304_if_no_change_meanwhile(self):
        self.resource.request.matchdict['id'] = self.stored['id']
        try:
            self.resource.get()
        except httpexceptions.HTTPNotModified as e:
            error = e
        self.assertEqual(error.code, 304)
        self.assertIsNotNone(error.headers.get('Last-Modified'))


class ModifiedMeanwhileTest(BaseTest):
    def setUp(self):
        super(ModifiedMeanwhileTest, self).setUp()
        self.stored = self.db.create(self.resource, 'bob', {})
        self.resource.collection_get()
        current = self.last_response.headers['Last-Modified']
        previous = six.text_type(int(current) - 10).encode('utf-8')
        self.resource.request.headers['If-Unmodified-Since'] = previous

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
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_single_record_returns_412_if_changed_meanwhile(self):
        self.resource.request.matchdict['id'] = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.get)

    def test_412_on_single_record_has_last_modified_timestamp(self):
        self.resource.request.matchdict['id'] = self.stored['id']
        try:
            self.resource.get()
        except httpexceptions.HTTPPreconditionFailed as e:
            error = e
        self.assertIsNotNone(error.headers.get('Last-Modified'))

    def test_create_returns_412_if_changed_meanwhile(self):
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.collection_post)

    def test_put_returns_412_if_changed_meanwhile(self):
        self.resource.request.matchdict['id'] = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.put)

    def test_patch_returns_412_if_changed_meanwhile(self):
        self.resource.request.matchdict['id'] = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.patch)

    def test_delete_returns_412_if_changed_meanwhile(self):
        self.resource.request.matchdict['id'] = self.stored['id']
        self.assertRaises(httpexceptions.HTTPPreconditionFailed,
                          self.resource.delete)
