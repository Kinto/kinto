import colander
import mock
import webtest
from cornice import Service
from pyramid import testing

from readinglist import set_auth, attach_http_objects
from readinglist.storage.memory import Memory
from readinglist.storage import exceptions as storage_exceptions
from readinglist.errors import ERRORS
from readinglist.resource import BaseResource, ResourceSchema, crud
from readinglist.tests.support import unittest, FakeAuthentMixin


class MushroomSchema(ResourceSchema):
    name = colander.SchemaNode(colander.String())


@crud()
class Mushroom(BaseResource):
    mapping = MushroomSchema()


MINIMALIST_RECORD = {'name': 'Champignon'}


class BaseWebTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.config = testing.setUp()
        self.config.registry.storage = Memory()

        Service.cors_origins = ('*',)

        set_auth(self.config)

        self.config.include("cornice")
        self.config.scan("readinglist.views")
        self.config.scan("readinglist.tests.resource.test_views")

        attach_http_objects(self.config)

        self.app = webtest.TestApp(self.config.make_wsgi_app())

        self.collection_url = '/mushrooms'
        self.item_url = '/mushrooms/{id}'

    def get_item_url(self, id=None):
        """Return the URL of the item using self.item_url."""
        if id is None:
            id = self.record['id']
        return self.item_url.format(id=id)


class AuthzAuthnTest(BaseWebTest):
    def test_all_views_require_authentication(self):
        self.app.get(self.collection_url, status=401)

        self.app.post(self.collection_url, MINIMALIST_RECORD, status=401)

        url = self.get_item_url('abc')
        self.app.get(url, status=401)
        self.app.patch(url, MINIMALIST_RECORD, status=401)
        self.app.delete(url, status=401)

    @mock.patch('readinglist.authentication.AuthorizationPolicy.permits')
    def test_view_permissions(self, permits_mocked):

        def permission_required():
            return permits_mocked.call_args[0][-1]

        self.app.get(self.collection_url)
        self.assertEqual(permission_required(), 'readonly')

        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD)
        self.assertEqual(permission_required(), 'readwrite')

        url = self.item_url.format(id=resp.json['id'])
        self.app.get(url)
        self.assertEqual(permission_required(), 'readonly')

        self.app.patch_json(url, {})
        self.assertEqual(permission_required(), 'readwrite')

        self.app.delete(url)
        self.assertEqual(permission_required(), 'readwrite')


class InvalidRecordTest(FakeAuthentMixin, BaseWebTest):
    def setUp(self):
        super(InvalidRecordTest, self).setUp()
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json

        self.invalid_record = {'name': 42}

    def test_invalid_record_returns_json_formatted_error(self):
        resp = self.app.post_json(self.collection_url,
                                  self.invalid_record,
                                  headers=self.headers,
                                  status=400)
        self.assertDictEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': "42 is not a string: {'name': ''}",  # XXX: weird msg
            'code': 400,
            'error': 'Invalid parameters'
        })

    def test_empty_body_returns_400(self):
        resp = self.app.post(self.collection_url,
                             '',
                             headers=self.headers,
                             status=400)
        self.assertEqual(resp.json['message'], 'name is missing')

    def test_create_invalid_record_returns_400(self):
        self.app.post_json(self.collection_url,
                           self.invalid_record,
                           headers=self.headers,
                           status=400)

    def test_modify_with_invalid_record_returns_400(self):
        self.app.patch_json(self.get_item_url(),
                            self.invalid_record,
                            headers=self.headers,
                            status=400)

    def test_replace_with_invalid_record_returns_400(self):
        self.app.put_json(self.get_item_url(),
                          self.invalid_record,
                          headers=self.headers,
                          status=400)


class InvalidBodyTest(FakeAuthentMixin, BaseWebTest):
    def __init__(self, *args, **kwargs):
        super(InvalidBodyTest, self).__init__(*args, **kwargs)
        self.headers.update({
            'Content-Type': 'application/json',
        })
        self.invalid_body = "{'foo>}"

    def setUp(self):
        super(InvalidBodyTest, self).setUp()
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json

    def test_invalid_body_returns_json_formatted_error(self):
        resp = self.app.post(self.collection_url,
                             self.invalid_body,
                             headers=self.headers,
                             status=400)
        error_msg = ("body: Invalid JSON request body: Expecting property name"
                     " enclosed in double quotes: line 1 column 2 (char 1)")
        self.assertDictEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': error_msg,
            'code': 400,
            'error': 'Invalid parameters'
        })

    def test_create_invalid_body_returns_400(self):
        self.app.post(self.collection_url,
                      self.invalid_body,
                      headers=self.headers,
                      status=400)

    def test_modify_with_invalid_body_returns_400(self):
        self.app.patch(self.get_item_url(),
                       self.invalid_body,
                       headers=self.headers,
                       status=400)

    def test_replace_with_invalid_body_returns_400(self):
        self.app.put(self.get_item_url(),
                     self.invalid_body,
                     headers=self.headers,
                     status=400)

    def test_invalid_uft8_returns_400(self):
        body = '{"foo": "\\u0d1"}'
        resp = self.app.post(self.collection_url,
                             body,
                             headers=self.headers,
                             status=400)
        self.assertIn('escape sequence', resp.json['message'])

    def test_modify_with_invalid_uft8_returns_400(self):
        body = '{"foo": "\\u0d1"}'
        resp = self.app.patch(self.get_item_url(),
                              body,
                              headers=self.headers,
                              status=400)
        self.assertIn('escape sequence', resp.json['message'])


class CORSHeadersTest(FakeAuthentMixin, BaseWebTest):
    def setUp(self):
        super(CORSHeadersTest, self).setUp()
        self.headers['Origin'] = 'notmyidea.org'

        response = self.app.post_json(self.collection_url,
                                      MINIMALIST_RECORD,
                                      headers=self.headers,
                                      status=201)
        self.record = response.json

    def test_present_on_hello(self):
        response = self.app.get('/',
                                headers=self.headers,
                                status=200)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_single_record(self):
        response = self.app.get(self.get_item_url(),
                                headers=self.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_deletion(self):
        response = self.app.delete(self.get_item_url(),
                                   headers=self.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_unknown_record(self):
        url = self.get_item_url('unknown')
        response = self.app.get(url,
                                headers=self.headers,
                                status=404)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_invalid_record_update(self):
        body = {'name': 42}
        response = self.app.patch_json(self.get_item_url(),
                                       body,
                                       headers=self.headers,
                                       status=400)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_successful_creation(self):
        response = self.app.post_json(self.collection_url,
                                      MINIMALIST_RECORD,
                                      headers=self.headers,
                                      status=201)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_invalid_record(self):
        body = {'name': 42}
        response = self.app.post_json(self.collection_url,
                                      body,
                                      headers=self.headers,
                                      status=400)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_unauthorized(self):
        self.headers.pop('Authorization', None)
        response = self.app.post_json(self.collection_url,
                                      MINIMALIST_RECORD,
                                      headers=self.headers,
                                      status=401)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_internal_error(self):
        with mock.patch('readinglist.views.article.Article.collection_get',
                        side_effect=ValueError):
            response = self.app.get('/articles',
                                    headers=self.headers, status=500)
        self.assertIn('Access-Control-Allow-Origin', response.headers)


class ConflictErrorsTest(FakeAuthentMixin, BaseWebTest):
    def setUp(self):
        super(ConflictErrorsTest, self).setUp()

        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json

        def unicity_failure(*args, **kwargs):
            raise storage_exceptions.UnicityError('city', {'id': 42})

        for operation in ('create', 'update'):
            patch = mock.patch.object(self.config.registry.storage, operation,
                                      side_effect=unicity_failure)
            patch.start()

    def test_409_error_gives_detail_about_field_and_record(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers,
                                  status=409)
        self.assertEqual(resp.json['message'],
                         'Conflict of field city on record 42')

    def test_post_returns_409(self):
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.headers,
                           status=409)

    def test_put_returns_409(self):
        self.app.put_json(self.get_item_url(),
                          MINIMALIST_RECORD,
                          headers=self.headers,
                          status=409)

    def test_patch_returns_409(self):
        body = {'name': 'Psylo'}
        self.app.patch_json(self.get_item_url(),
                            body,
                            headers=self.headers,
                            status=409)
