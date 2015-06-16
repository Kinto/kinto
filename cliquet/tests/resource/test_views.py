import mock
import webtest
import uuid
from pyramid import testing

import cliquet
from cliquet.storage import exceptions as storage_exceptions
from cliquet.errors import ERRORS
from cliquet.tests.support import unittest, get_request_class, USER_PRINCIPAL


MINIMALIST_RECORD = {'name': 'Champignon'}


class BaseWebTest(unittest.TestCase):
    authorization_policy = 'cliquet.tests.support.AllowAuthorizationPolicy'
    collection_url = '/mushrooms'

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.config = testing.setUp()

        self.config.add_settings({
            'cliquet.storage_backend': 'cliquet.storage.memory',
            'cliquet.project_version': '0.0.1',
            'cliquet.project_name': 'cliquet',
            'cliquet.project_docs': 'https://cliquet.rtfd.org/',
            'multiauth.authorization_policy': self.authorization_policy
        })

        cliquet.initialize(self.config)
        self.config.scan("cliquet.tests.testapp.views")

        self.app = webtest.TestApp(self.config.make_wsgi_app())
        self.app.RequestClass = get_request_class(self.config.route_prefix)
        self.item_url = '/mushrooms/{id}'
        self.principal = USER_PRINCIPAL

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic bWF0OjE='
        }

    def tearDown(self):
        self.app.app.registry.permission.flush()

    def get_item_url(self, id=None):
        """Return the URL of the item using self.item_url."""
        if id is None:
            id = self.record['id']
        return self.collection_url + '/' + str(id)


class AuthzAuthnTest(BaseWebTest):
    authorization_policy = 'cliquet.authorization.AuthorizationPolicy'

    def add_permission(self, object_id, permission):
        self.app.app.registry.permission.add_principal_to_ace(
            object_id, permission, self.principal)


class ProtectedResourcePermissionTest(AuthzAuthnTest):
    # Protected resource.
    collection_url = '/toadstools'

    def setUp(self):
        self.add_permission(self.collection_url, 'toadstool:create')

    def test_permissions_are_associated_to_object_uri_without_prefix(self):
        body = {'data': MINIMALIST_RECORD,
                'permissions': {'read': ['group:readers']}}
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers)
        object_uri = '/toadstools/%s' % resp.json['data']['id']
        backend = self.app.app.registry.permission
        stored_perms = backend.object_permission_principals(object_uri, 'read')
        self.assertEqual(stored_perms, {'group:readers'})

    def test_permissions_are_not_modified_if_not_specified(self):
        body = {'data': MINIMALIST_RECORD,
                'permissions': {'read': ['group:readers']}}
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers)
        object_uri = self.get_item_url(resp.json['data']['id'])
        body.pop('permissions')

        self.add_permission(object_uri, 'write')
        resp = self.app.put_json(object_uri, body, headers=self.headers)
        self.assertEqual(resp.json['permissions']['read'], ['group:readers'])

    def test_unknown_permissions_are_not_accepted(self):
        self.maxDiff = None
        body = {'data': MINIMALIST_RECORD,
                'permissions': {'read': ['group:readers'],
                                'unknown': ['jacques']}}
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers, status=400)
        self.assertEqual(
            resp.json['message'],
            'permissions in body: "unknown" is not one of read, write')


class CollectionAuthzGrantedTest(AuthzAuthnTest):
    def test_collection_get_is_granted_when_authorized(self):
        self.add_permission(self.collection_url, 'read')
        self.app.get(self.collection_url, headers=self.headers, status=200)

    def test_collection_post_is_granted_when_authorized(self):
        self.add_permission(self.collection_url, 'mushroom:create')
        self.app.post_json(self.collection_url, {'data': MINIMALIST_RECORD},
                           headers=self.headers, status=201)

    def test_collection_delete_is_granted_when_authorized(self):
        self.add_permission(self.collection_url, 'write')
        self.app.delete(self.collection_url, headers=self.headers, status=200)


class CollectionAuthzDeniedTest(AuthzAuthnTest):
    def test_views_require_authentication(self):
        self.app.get(self.collection_url, status=401)

        body = {'data': MINIMALIST_RECORD}
        self.app.post_json(self.collection_url, body, status=401)

    def test_collection_get_is_denied_when_not_authorized(self):
        self.app.get(self.collection_url, headers=self.headers, status=403)

    def test_collection_post_is_denied_when_not_authorized(self):
        self.app.post_json(self.collection_url, {'data': MINIMALIST_RECORD},
                           headers=self.headers, status=403)

    def test_collection_delete_is_denied_when_not_authorized(self):
        self.app.delete(self.collection_url, headers=self.headers, status=403)


class RecordAuthzGrantedTest(AuthzAuthnTest):
    def setUp(self):
        super(RecordAuthzGrantedTest, self).setUp()
        self.add_permission(self.collection_url, 'mushroom:create')

        resp = self.app.post_json(self.collection_url,
                                  {'data': MINIMALIST_RECORD},
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self.get_item_url()
        self.unknown_record_url = self.get_item_url(uuid.uuid4())

    def test_record_get_is_granted_when_authorized(self):
        self.add_permission(self.record_url, 'read')
        self.app.get(self.record_url, headers=self.headers, status=200)

    def test_record_patch_is_granted_when_authorized(self):
        self.add_permission(self.record_url, 'write')
        self.app.patch_json(self.record_url, {'data': MINIMALIST_RECORD},
                            headers=self.headers, status=200)

    def test_record_delete_is_granted_when_authorized(self):
        self.add_permission(self.record_url, 'write')
        self.app.delete(self.record_url, headers=self.headers, status=200)

    def test_record_put_on_existing_record_is_granted_when_authorized(self):
        self.add_permission(self.record_url, 'write')
        self.app.put_json(self.record_url, {'data': MINIMALIST_RECORD},
                          headers=self.headers, status=200)

    def test_record_put_on_unexisting_record_is_granted_when_authorized(self):
        self.add_permission(self.collection_url, 'mushroom:create')
        self.app.put_json(self.unknown_record_url, {'data': MINIMALIST_RECORD},
                          headers=self.headers, status=201)


class RecordAuthzDeniedTest(AuthzAuthnTest):
    def setUp(self):
        super(RecordAuthzDeniedTest, self).setUp()
        self.app.app.registry.permission.add_principal_to_ace(
            self.collection_url, 'mushroom:create', self.principal)

        resp = self.app.post_json(self.collection_url,
                                  {'data': MINIMALIST_RECORD},
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self.get_item_url()
        self.unknown_record_url = self.get_item_url(uuid.uuid4())

    def test_views_require_authentication(self):
        url = self.get_item_url('abc')
        self.app.get(url, status=401)
        self.app.patch_json(url, {'data': MINIMALIST_RECORD}, status=401)
        self.app.delete(url, status=401)

    def test_record_get_is_denied_when_not_authorized(self):
        self.app.get(self.record_url, headers=self.headers, status=403)

    def test_record_patch_is_denied_when_not_authorized(self):
        self.app.patch_json(self.record_url, {'data': MINIMALIST_RECORD},
                            headers=self.headers, status=403)

    def test_record_put_is_denied_when_not_authorized(self):
        self.app.put_json(self.record_url, {'data': MINIMALIST_RECORD},
                          headers=self.headers, status=403)

    def test_record_delete_is_denied_when_not_authorized(self):
        self.app.delete(self.record_url, headers=self.headers, status=403)

    def test_record_put_on_unexisting_record_is_rejected_if_write_perm(self):
        object_id = self.collection_url
        self.app.app.registry.permission.remove_principal_from_ace(
            object_id, 'mushroom:create', self.principal)  # Was added in setUp

        self.app.app.registry.permission.add_principal_to_ace(
            object_id, 'write', self.principal)
        self.app.put_json(self.unknown_record_url, {'data': MINIMALIST_RECORD},
                          headers=self.headers, status=403)


class InvalidRecordTest(BaseWebTest):
    def setUp(self):
        super(InvalidRecordTest, self).setUp()
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json['data']

        self.invalid_record = {'data': {'name': 42}}

    def test_invalid_record_returns_json_formatted_error(self):
        resp = self.app.post_json(self.collection_url,
                                  self.invalid_record,
                                  headers=self.headers,
                                  status=400)
        # XXX: weird resp.json['message']
        self.assertDictEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': "data.name in body: 42 is not a string: {'name': ''}",
            'code': 400,
            'error': 'Invalid parameters',
            'details': [{'description': "42 is not a string: {'name': ''}",
                         'location': 'body',
                         'name': 'data.name'}]})

    def test_empty_body_returns_400(self):
        resp = self.app.post(self.collection_url,
                             '',
                             headers=self.headers,
                             status=400)
        self.assertEqual(resp.json['message'], 'data is missing')

    def test_unknown_attribute_returns_400(self):
        resp = self.app.post(self.collection_url,
                             '{"data": {"name": "ML"}, "datta": {}}',
                             headers=self.headers,
                             status=400)
        self.assertEqual(resp.json['message'], 'datta is not allowed')

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

    def test_id_is_validated_on_post(self):
        record = MINIMALIST_RECORD.copy()
        record['id'] = 3.14
        self.app.post_json(self.collection_url,
                           {'data': record},
                           headers=self.headers,
                           status=400)

    def test_id_is_preserved_on_post(self):
        record = MINIMALIST_RECORD.copy()
        record_id = record['id'] = '472be9ec-26fe-461b-8282-9c4e4b207ab3'
        resp = self.app.post_json(self.collection_url,
                                  {'data': record},
                                  headers=self.headers)
        self.assertEqual(resp.json['data']['id'], record_id)

    def test_200_is_returned_if_id_matches_existing_record(self):
        record = MINIMALIST_RECORD.copy()
        record['id'] = self.record['id']
        self.app.post_json(self.collection_url,
                           {'data': record},
                           headers=self.headers,
                           status=200)


class IgnoredFieldsTest(BaseWebTest):
    def setUp(self):
        super(IgnoredFieldsTest, self).setUp()
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json['data']

    def test_last_modified_is_not_validated_and_overwritten(self):
        record = MINIMALIST_RECORD.copy()
        record['last_modified'] = 'abc'
        body = {'data': record}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.assertNotEqual(resp.json['data']['last_modified'], 'abc')

    def test_modify_works_with_invalid_last_modified(self):
        body = {'data': {'last_modified': 'abc'}}
        resp = self.app.patch_json(self.get_item_url(),
                                   body,
                                   headers=self.headers)
        self.assertNotEqual(resp.json['data']['last_modified'], 'abc')

    def test_replace_works_with_invalid_last_modified(self):
        record = MINIMALIST_RECORD.copy()
        record['last_modified'] = 'abc'
        body = {'data': record}
        resp = self.app.put_json(self.get_item_url(),
                                 body,
                                 headers=self.headers)
        self.assertNotEqual(resp.json['data']['last_modified'], 'abc')


class InvalidBodyTest(BaseWebTest):
    def __init__(self, *args, **kwargs):
        super(InvalidBodyTest, self).__init__(*args, **kwargs)
        self.invalid_body = "{'foo>}"

    def setUp(self):
        super(InvalidBodyTest, self).setUp()
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json['data']

    def test_invalid_body_returns_json_formatted_error(self):
        resp = self.app.post(self.collection_url,
                             self.invalid_body,
                             headers=self.headers,
                             status=400)
        error_msg = ("Invalid JSON request body: Expecting property name"
                     " enclosed in double quotes: line 1 column 2 (char 1)")
        self.assertDictEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': "body: %s" % error_msg,
            'code': 400,
            'error': 'Invalid parameters',
            'details': [
                {'description': error_msg,
                 'location': 'body',
                 'name': None},
                {'description': 'data is missing',
                 'location': 'body',
                 'name': 'data'}]})

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

    def test_modify_with_empty_returns_400(self):
        resp = self.app.patch(self.get_item_url(),
                              '',
                              headers=self.headers,
                              status=400)
        self.assertIn('Empty body', resp.json['message'])


class InvalidPermissionsTest(BaseWebTest):
    def setUp(self):
        super(InvalidPermissionsTest, self).setUp()
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.invalid_body = {'data': MINIMALIST_RECORD,
                             'permissions': {'read': 'book'}}

    def test_create_invalid_body_returns_400(self):
        self.app.post_json(self.collection_url,
                           self.invalid_body,
                           headers=self.headers,
                           status=400)

    def test_invalid_body_returns_json_formatted_error(self):
        resp = self.app.post_json(self.collection_url,
                                  self.invalid_body,
                                  headers=self.headers,
                                  status=400)
        self.assertDictEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS,
            'message': 'permissions.read in body: "book" is not iterable',
            'code': 400,
            'error': 'Invalid parameters',
            'details': [
                {'description': '"book" is not iterable',
                 'location': 'body',
                 'name': 'permissions.read'}]})


class ConflictErrorsTest(BaseWebTest):
    def setUp(self):
        super(ConflictErrorsTest, self).setUp()

        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json['data']

        def unicity_failure(*args, **kwargs):
            raise storage_exceptions.UnicityError('city', {'id': 42})

        for operation in ('create', 'update'):
            patch = mock.patch.object(self.config.registry.storage, operation,
                                      side_effect=unicity_failure)
            patch.start()

    def test_post_returns_200_with_existing_record(self):
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.assertEqual(resp.json['data'], {'id': 42})

    def test_put_returns_409(self):
        body = {'data': MINIMALIST_RECORD}
        self.app.put_json(self.get_item_url(),
                          body,
                          headers=self.headers,
                          status=409)

    def test_patch_returns_409(self):
        body = {'data': {'name': 'Psylo'}}
        self.app.patch_json(self.get_item_url(),
                            body,
                            headers=self.headers,
                            status=409)

    def test_409_error_gives_detail_about_field_and_record(self):
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.put_json(self.get_item_url(),
                                 body,
                                 headers=self.headers,
                                 status=409)
        self.assertEqual(resp.json['message'],
                         'Conflict of field city on record 42')
        self.assertEqual(resp.json['details']['field'], 'city')
        self.assertEqual(resp.json['details']['existing'], {'id': 42})


class StorageErrorTest(BaseWebTest):
    def __init__(self, *args, **kwargs):
        super(StorageErrorTest, self).__init__(*args, **kwargs)
        self.error = storage_exceptions.BackendError(ValueError())
        self.storage_error_patcher = mock.patch(
            'cliquet.storage.memory.Memory.create',
            side_effect=self.error)

    def test_backend_errors_are_served_as_503(self):
        body = {'data': MINIMALIST_RECORD}
        with self.storage_error_patcher:
            self.app.post_json(self.collection_url,
                               body,
                               headers=self.headers,
                               status=503)

    def test_backend_errors_original_error_is_logged(self):
        body = {'data': MINIMALIST_RECORD}
        with mock.patch('cliquet.views.errors.logger.critical') as mocked:
            with self.storage_error_patcher:
                self.app.post_json(self.collection_url,
                                   body,
                                   headers=self.headers,
                                   status=503)
                self.assertTrue(mocked.called)
                self.assertEqual(type(mocked.call_args[0][0]), ValueError)


class PaginationNextURLTest(BaseWebTest):
    """Extra tests for `cliquet.tests.resource.test_pagination`
    """

    def setUp(self):
        super(PaginationNextURLTest, self).setUp()
        body = {'data': MINIMALIST_RECORD}
        self.app.post_json(self.collection_url,
                           body,
                           headers=self.headers)
        self.app.post_json(self.collection_url,
                           body,
                           headers=self.headers)

    def test_next_page_url_has_got_port_number_if_different_than_80(self):
        resp = self.app.get(self.collection_url + '?_limit=1',
                            extra_environ={'HTTP_HOST': 'localhost:8000'},
                            headers=self.headers)
        self.assertIn(':8000', resp.headers['Next-Page'])

    def test_next_page_url_has_not_port_number_if_80(self):
        resp = self.app.get(self.collection_url + '?_limit=1',
                            extra_environ={'HTTP_HOST': 'localhost:80'},
                            headers=self.headers)
        self.assertNotIn(':80', resp.headers['Next-Page'])

    def test_next_page_url_relies_on_pyramid_url_system(self):
        resp = self.app.get(self.collection_url + '?_limit=1',
                            extra_environ={'wsgi.url_scheme': 'https'},
                            headers=self.headers)
        self.assertIn('https://', resp.headers['Next-Page'])

    def test_next_page_url_relies_on_headers_information(self):
        headers = self.headers.copy()
        headers['Host'] = 'https://server.name:443'
        resp = self.app.get(self.collection_url + '?_limit=1',
                            headers=headers)
        self.assertIn('https://server.name:443', resp.headers['Next-Page'])
