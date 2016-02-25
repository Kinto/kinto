import mock
import uuid

from cliquet.storage import exceptions as storage_exceptions
from cliquet.errors import ERRORS
from cliquet.tests.support import unittest, BaseWebTest


MINIMALIST_RECORD = {'name': 'Champignon'}


class UserResourcePermissionTest(BaseWebTest, unittest.TestCase):
    authorization_policy = 'cliquet.authorization.AuthorizationPolicy'

    def test_views_require_authentication(self):
        self.app.get(self.collection_url, status=401)
        body = {'data': MINIMALIST_RECORD}
        self.app.post_json(self.collection_url, body, status=401)
        record_url = self.get_item_url('abc')
        self.app.get(record_url, status=401)
        self.app.put_json(record_url, body, status=401)
        self.app.patch_json(record_url, body, status=401)
        self.app.delete(record_url, status=401)

    def test_collection_operations_are_authorized_if_authenticated(self):
        body = {'data': MINIMALIST_RECORD}
        self.app.get(self.collection_url, headers=self.headers, status=200)
        self.app.post_json(self.collection_url, body,
                           headers=self.headers, status=201)
        self.app.delete(self.collection_url, headers=self.headers, status=200)

    def test_record_operations_are_authorized_if_authenticated(self):
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers, status=201)
        record = resp.json['data']
        record_url = self.get_item_url(record['id'])
        unknown_url = self.get_item_url(uuid.uuid4())

        self.app.get(record_url, headers=self.headers, status=200)
        self.app.patch_json(record_url, body, headers=self.headers, status=200)
        self.app.delete(record_url, headers=self.headers, status=200)
        self.app.put_json(record_url, body, headers=self.headers, status=201)
        self.app.put_json(unknown_url, body, headers=self.headers, status=201)


class AuthzAuthnTest(BaseWebTest, unittest.TestCase):
    authorization_policy = 'cliquet.authorization.AuthorizationPolicy'
    # Shareable resource.
    collection_url = '/toadstools'

    def add_permission(self, object_id, permission, principal=None):
        if not principal:
            principal = self.principal
        self.permission.add_principal_to_ace(object_id, permission, principal)


class ShareableResourcePermissionTest(AuthzAuthnTest):
    def setUp(self):
        self.add_permission(self.collection_url, 'toadstool:create')

    def test_permissions_are_associated_to_object_uri_without_prefix(self):
        body = {'data': MINIMALIST_RECORD,
                'permissions': {'read': ['group:readers']}}
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers)
        object_uri = self.get_item_url(resp.json['data']['id'])
        backend = self.permission
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

    def test_permissions_can_be_modified_using_patch(self):
        body = {'data': MINIMALIST_RECORD,
                'permissions': {'read': ['group:readers']}}
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers)
        body = {'permissions': {'read': ['fxa:user']}}
        uri = self.get_item_url(resp.json['data']['id'])
        resp = self.app.patch_json(uri, body, headers=self.headers)
        principals = resp.json['permissions']['read']
        self.assertEqual(sorted(principals), ['fxa:user'])

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
        self.add_permission(self.collection_url, 'toadstool:create')
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
        self.add_permission(self.collection_url, 'toadstool:create')

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
        self.add_permission(self.collection_url, 'toadstool:create')
        self.app.put_json(self.unknown_record_url, {'data': MINIMALIST_RECORD},
                          headers=self.headers, status=201)


class RecordAuthzDeniedTest(AuthzAuthnTest):
    def setUp(self):
        super(RecordAuthzDeniedTest, self).setUp()
        # Add permission to create a sample record.
        self.add_permission(self.collection_url, 'toadstool:create')
        resp = self.app.post_json(self.collection_url,
                                  {'data': MINIMALIST_RECORD},
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self.get_item_url()
        self.unknown_record_url = self.get_item_url(uuid.uuid4())
        # Remove every permissions.
        self.permission.flush()

    def test_views_require_authentication(self):
        url = self.get_item_url('abc')
        self.app.get(url, status=401)
        self.app.put_json(url, {'data': MINIMALIST_RECORD}, status=401)
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
        self.permission.remove_principal_from_ace(
            object_id, 'toadstool:create', self.principal)  # Added in setUp.

        self.permission.add_principal_to_ace(
            object_id, 'write', self.principal)
        self.app.put_json(self.unknown_record_url, {'data': MINIMALIST_RECORD},
                          headers=self.headers, status=403)


class RecordAuthzGrantedOnCollectionTest(AuthzAuthnTest):
    def setUp(self):
        super(RecordAuthzGrantedOnCollectionTest, self).setUp()
        self.add_permission(self.collection_url, 'toadstool:create')

        self.guest_headers = self.headers.copy()
        self.guest_headers['Authorization'] = "Basic bmF0aW06"
        resp = self.app.get('/', headers=self.guest_headers)
        self.guest_id = resp.json['user']['id']

        body = {
            'data': MINIMALIST_RECORD,
            'permissions': {
                'write': [self.guest_id],
                'read': [self.guest_id]
            }
        }
        resp = self.app.post_json(self.collection_url, body,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.record_url = self.get_item_url()

        # Add another private record
        resp = self.app.post_json(self.collection_url,
                                  {'data': MINIMALIST_RECORD,
                                   'permissions': {"read": [self.principal]}},
                                  headers=self.headers)

    def test_guest_can_access_the_record(self):
        self.app.get(self.record_url, headers=self.guest_headers, status=200)

    def test_guest_can_see_the_record_in_the_list_of_records(self):
        resp = self.app.get(self.collection_url, headers=self.guest_headers,
                            status=200)
        self.assertEqual(len(resp.json['data']), 1)

    def test_guest_can_remove_its_records_from_the_list_of_records(self):
        resp = self.app.delete(self.collection_url, headers=self.guest_headers,
                               status=200)
        self.assertEqual(len(resp.json['data']), 1)
        resp = self.app.get(self.collection_url, headers=self.headers,
                            status=200)
        self.assertEqual(len(resp.json['data']), 1)


class EmptySchemaTest(BaseWebTest, unittest.TestCase):
    collection_url = '/moistures'

    def test_accept_empty_body(self):
        resp = self.app.post(self.collection_url,
                             headers=self.headers)
        self.assertIn('id', resp.json['data'])
        resp = self.app.put(self.get_item_url(uuid.uuid4()),
                            headers=self.headers)
        self.assertIn('id', resp.json['data'])

    def test_data_can_be_specified(self):
        resp = self.app.post_json(self.collection_url,
                                  {'data': {}},
                                  headers=self.headers)
        self.assertIn('id', resp.json['data'])

    def test_data_fields_are_ignored(self):
        resp = self.app.post_json(self.collection_url,
                                  {'data': {'icq': '9427392'}},
                                  headers=self.headers)
        self.assertNotIn('icq', resp.json['data'])


class OptionalSchemaTest(EmptySchemaTest):
    collection_url = '/psilos'

    def test_known_fields_are_saved(self):
        resp = self.app.post_json(self.collection_url,
                                  {'data': {'edible': False}},
                                  headers=self.headers)
        self.assertIn('edible', resp.json['data'])


class InvalidRecordTest(BaseWebTest, unittest.TestCase):
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
            'errno': ERRORS.INVALID_PARAMETERS.value,
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

    def test_modify_with_unknown_attribute_returns_400(self):
        self.app.patch_json(self.get_item_url(),
                            {"datta": {}},
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

    def test_invalid_accept_header_on_collections_returns_406(self):
        headers = self.headers.copy()
        headers['Accept'] = 'text/plain'
        resp = self.app.post(self.collection_url,
                             '',
                             headers=headers,
                             status=406)
        self.assertEqual(resp.json['code'], 406)
        message = "Accept header should be one of ['application/json']"
        self.assertEqual(resp.json['message'], message)

    def test_invalid_content_type_header_on_collections_returns_415(self):
        headers = self.headers.copy()
        headers['Content-Type'] = 'text/plain'
        resp = self.app.post(self.collection_url,
                             '',
                             headers=headers,
                             status=415)
        self.assertEqual(resp.json['code'], 415)
        message = "Content-Type header should be one of ['application/json']"
        self.assertEqual(resp.json['message'], message)

    def test_invalid_accept_header_on_record_returns_406(self):
        headers = self.headers.copy()
        headers['Accept'] = 'text/plain'
        resp = self.app.get(self.get_item_url(),
                            headers=headers,
                            status=406)
        self.assertEqual(resp.json['code'], 406)
        message = "Accept header should be one of ['application/json']"
        self.assertEqual(resp.json['message'], message)

    def test_invalid_content_type_header_on_record_returns_415(self):
        headers = self.headers.copy()
        headers['Content-Type'] = 'text/plain'
        resp = self.app.patch_json(self.get_item_url(),
                                   '',
                                   headers=headers,
                                   status=415)
        self.assertEqual(resp.json['code'], 415)
        message = "Content-Type header should be one of ['application/json']"
        self.assertEqual(resp.json['message'], message)


class IgnoredFieldsTest(BaseWebTest, unittest.TestCase):
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


class InvalidBodyTest(BaseWebTest, unittest.TestCase):
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
            'errno': ERRORS.INVALID_PARAMETERS.value,
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

    def test_modify_with_empty_body_returns_400(self):
        self.app.patch(self.get_item_url(),
                       headers=self.headers,
                       status=400)

    def test_modify_shareable_resource_with_empty_body_returns_400(self):
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json('/toadstools',
                                  body,
                                  headers=self.headers)
        record = resp.json['data']
        item_url = '/toadstools/' + record['id']
        self.app.patch(item_url,
                       headers=self.headers,
                       status=400)


class InvalidPermissionsTest(BaseWebTest, unittest.TestCase):
    collection_url = '/toadstools'

    def setUp(self):
        super(InvalidPermissionsTest, self).setUp()
        body = {'data': MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json['data']
        self.invalid_body = {'data': MINIMALIST_RECORD,
                             'permissions': {'read': 'book'}}  # book not list

    def test_permissions_are_not_accepted_on_normal_resources(self):
        body = {'data': MINIMALIST_RECORD,
                'permissions': {'read': ['book']}}
        resp = self.app.post_json('/mushrooms', body, headers=self.headers,
                                  status=400)
        self.assertEqual(resp.json['message'], 'permissions is not allowed')

    def test_create_invalid_body_returns_400(self):
        self.app.post_json(self.collection_url,
                           self.invalid_body,
                           headers=self.headers,
                           status=400)

    def test_modify_with_invalid_permissions_returns_400(self):
        self.app.patch_json(self.get_item_url(),
                            self.invalid_body,
                            headers=self.headers,
                            status=400)

    def test_invalid_body_returns_json_formatted_error(self):
        resp = self.app.post_json(self.collection_url,
                                  self.invalid_body,
                                  headers=self.headers,
                                  status=400)
        self.assertDictEqual(resp.json, {
            'errno': ERRORS.INVALID_PARAMETERS.value,
            'message': 'permissions.read in body: "book" is not iterable',
            'code': 400,
            'error': 'Invalid parameters',
            'details': [
                {'description': '"book" is not iterable',
                 'location': 'body',
                 'name': 'permissions.read'}]})


class ConflictErrorsTest(BaseWebTest, unittest.TestCase):
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
            patch = mock.patch.object(self.storage, operation,
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


class CacheControlTest(BaseWebTest, unittest.TestCase):
    collection_url = '/toadstools'

    def get_app_settings(self, extras=None):
        settings = super(CacheControlTest, self).get_app_settings(extras)
        settings['toadstool_cache_expires_seconds'] = 3600
        settings['toadstool_read_principals'] = 'system.Everyone'
        settings['psilo_cache_expires_seconds'] = 0
        settings['moisture_read_principals'] = 'system.Everyone'
        return settings

    def test_cache_control_headers_are_set_if_anonymous(self):
        resp = self.app.get(self.collection_url)
        self.assertIn('Expires', resp.headers)
        self.assertIn('Cache-Control', resp.headers)

    def test_cache_control_headers_are_not_set_if_authenticated(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        self.assertIn('no-cache', resp.headers['Cache-Control'])
        self.assertNotIn('Expires', resp.headers)

    def test_cache_control_headers_set_no_cache_if_zero(self):
        resp = self.app.get('/psilos')
        self.assertIn('Cache-Control', resp.headers)
        # Check that not set by Pyramid.cache_expires()
        self.assertNotIn('Expires', resp.headers)

    def test_cache_control_provides_no_cache_by_default(self):
        resp = self.app.get('/moistures')
        self.assertIn('no-cache', resp.headers['Cache-Control'])
        self.assertNotIn('Expires', resp.headers)


class StorageErrorTest(BaseWebTest, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(StorageErrorTest, self).__init__(*args, **kwargs)
        self.error = storage_exceptions.BackendError(ValueError())
        self.storage_error_patcher = mock.patch(
            'cliquet.storage.redis.Storage.create',
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


class PaginationNextURLTest(BaseWebTest, unittest.TestCase):
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


class SchemaLessPartialResponseTest(BaseWebTest, unittest.TestCase):
    """Extra tests for :mod:`cliquet.tests.resource.test_partial_response`
    """
    collection_url = '/spores'

    def setUp(self):
        super(SchemaLessPartialResponseTest, self).setUp()
        body = {'data': {'size': 42, 'category': 'some-cat', 'owner': 'loco'}}
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.record = resp.json

    def test_unspecified_fields_are_excluded(self):
        resp = self.app.get(self.collection_url + '?_fields=size,category')
        result = resp.json['data'][0]
        self.assertNotIn('owner', result)

    def test_specified_fields_are_included(self):
        resp = self.app.get(self.collection_url + '?_fields=size,category')
        result = resp.json['data'][0]
        self.assertIn('size', result)
        self.assertIn('category', result)

    def test_unknown_fields_are_ignored(self):
        resp = self.app.get(self.collection_url + '?_fields=nationality')
        result = resp.json['data'][0]
        self.assertNotIn('nationality', result)
