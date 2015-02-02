import colander
from cornice import Service
import mock
from pyramid import testing
import webtest

from readinglist import set_auth, attach_http_objects
from readinglist.backend.memory import Memory
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

    def setUp(self):
        self.config = testing.setUp()
        self.config.registry.backend = Memory()

        Service.cors_origins = ('*',)

        set_auth(self.config)

        self.config.include("cornice")
        self.config.scan("readinglist.views")
        self.config.scan("readinglist.tests.resource.test_views")

        attach_http_objects(self.config)

        self.app = webtest.TestApp(self.config.make_wsgi_app())

        self.collection_url = '/mushrooms'
        self.item_url = '/mushrooms/{id}'


class AuthzAuthnTest(BaseWebTest):
    def test_all_views_require_authentication(self):
        self.app.get(self.collection_url, status=401)

        self.app.post(self.collection_url, MINIMALIST_RECORD, status=401)

        url = self.item_url.format(id='abc')
        self.app.get(url, status=401)
        self.app.patch(url, MINIMALIST_RECORD, status=401)
        self.app.delete(url, status=401)

    @mock.patch('readinglist.authentication.AuthorizationPolicy.permits')
    def test_view_permissions(self, permits_mocked):
        permission_required = lambda: permits_mocked.call_args[0][-1]

        self.app.get(self.collection_url)
        self.assertEqual(permission_required(), 'readonly')

        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD)
        self.assertEqual(permission_required(), 'readwrite')

        url = self.item_url.format(id=resp.json['_id'])
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
        self.assertEqual(resp.json, {
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
        url = self.item_url.format(id=self.record['_id'])
        self.app.patch_json(url,
                            self.invalid_record,
                            headers=self.headers,
                            status=400)

    def test_replace_with_invalid_record_returns_400(self):
        url = self.item_url.format(id=self.record['_id'])
        self.app.put_json(url,
                          self.invalid_record,
                          headers=self.headers,
                          status=400)


class InvalidBodyTest(FakeAuthentMixin, BaseWebTest):
    def setUp(self):
        super(InvalidBodyTest, self).setUp()
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        self.record = resp.json

        self.invalid_body = "{'foo>}"

    def test_invalid_body_returns_json_formatted_error(self):
        resp = self.app.post(self.collection_url,
                             self.invalid_body,
                             headers=self.headers,
                             status=400)
        self.assertEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': 'Invalid JSON request body',
            'code': 400,
            'error': 'Invalid parameters'
        })

    def test_create_invalid_body_returns_400(self):
        self.app.post(self.collection_url,
                      self.invalid_body,
                      headers=self.headers,
                      status=400)

    def test_modify_with_invalid_body_returns_400(self):
        url = self.item_url.format(id=self.record['_id'])
        self.app.patch(url,
                       self.invalid_body,
                       headers=self.headers,
                       status=400)

    def test_replace_with_invalid_body_returns_400(self):
        url = self.item_url.format(id=self.record['_id'])
        self.app.put(url,
                     self.invalid_body,
                     headers=self.headers,
                     status=400)

    def test_invalid_uft8_returns_400(self):
        body = '{"foo": "\\u0d1"}'
        resp = self.app.post(self.collection_url,
                             body,
                             headers=self.headers,
                             status=400)
        self.assertIn('Invalid \uXXXX escape sequence', resp.json['message'])

    def test_modify_with_invalid_uft8_returns_400(self):
        url = self.item_url.format(id=self.record['_id'])
        body = '{"foo": "\\u0d1"}'
        resp = self.app.patch(url,
                              body,
                              headers=self.headers,
                              status=400)
        self.assertIn('Invalid \uXXXX escape sequence', resp.json['message'])


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
        url = self.item_url.format(id=self.record['_id'])
        response = self.app.get(url,
                                headers=self.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_deletion(self):
        url = self.item_url.format(id=self.record['_id'])
        response = self.app.delete(url,
                                   headers=self.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_present_on_unknown_record(self):
        url = self.item_url.format(id='unknown')
        response = self.app.get(url,
                                headers=self.headers,
                                status=404)
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
        with mock.patch('traceback.format_exc', return_value="") as mock_err:
            with mock.patch('readinglist.views.article.Article.collection_get',
                            side_effect=ValueError):
                response = self.app.get('/articles',
                                        headers=self.headers, status=500)
        mock_err.assert_called_once_with()
        self.assertIn('Access-Control-Allow-Origin', response.headers)
