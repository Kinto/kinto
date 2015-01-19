import mock
import webtest

from readinglist import API_VERSION
from readinglist.errors import ERRORS


class PrefixedRequestClass(webtest.app.TestRequest):

    @classmethod
    def blank(cls, path, *args, **kwargs):
        path = '/%s%s' % (API_VERSION, path)
        return webtest.app.TestRequest.blank(path, *args, **kwargs)


class BaseWebTest(object):
    """Base Web Test to test your cornice service.

    It setups the database before each test and delete it after.
    """

    def setUp(self):
        self.app = webtest.TestApp("config:conf/readinglist.ini",
                                   relative_to='.')
        self.app.RequestClass = PrefixedRequestClass
        self.db = self.app.app.registry.backend

        self.patcher = mock.patch('readinglist.authentication.'
                                  'OAuthClient.verify_token')
        self.fxa_verify = self.patcher.start()
        self.fxa_verify.return_value = {
            'user': 'bob'
        }

        access_token = 'secret'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(access_token),
        }

    def tearDown(self):
        self.db.flush()
        self.patcher.stop()

    def assertFormattedError(self, response, code, errno, error,
                             message=None, info=None):
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=UTF-8')
        self.assertEqual(response.json['code'], code)
        self.assertEqual(response.json['errno'], errno)
        self.assertEqual(response.json['error'], error)

        if message is not None:
            self.assertEqual(response.json['message'], message)
        else:
            self.assertNotIn('message', response.json)

        if info is not None:
            self.assertEqual(response.json['info'], info)
        else:
            self.assertNotIn('info', response.json)


class BaseResourceViewsTest(BaseWebTest):
    resource_class = None

    def setUp(self):
        super(BaseResourceViewsTest, self).setUp()
        self.resource = self.resource_class(mock.MagicMock())

        resource_name = self.resource_class.__name__.lower()
        self.collection_url = '/%ss' % resource_name
        self.item_url = '/%ss/{id}' % resource_name
        self.record = self._createRecord()

    def _createRecord(self):
        resp = self.app.post_json(self.collection_url,
                                  self.record_factory(),
                                  headers=self.headers)
        return resp.json

    def assertRecordEquals(self, record1, record2):
        return self.assertEqual(record1, record2)

    def assertRecordNotEquals(self, record1, record2):
        return self.assertNotEqual(record1, record2)

    def record_factory(self):
        raise NotImplementedError

    def invalid_record_factory(self):
        return dict(foo="bar")

    def modify_record(self, original):
        raise NotImplementedError

    def test_list(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['items']
        self.assertEquals(len(records), 1)
        self.assertRecordEquals(records[0], self.record)

    def test_list_gives_number_of_results(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        meta = resp.json['meta']
        self.assertEquals(meta['total'], 1)

    def test_list_is_filtered_by_user(self):
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['items']
        self.assertEquals(len(records), 0)

    def test_create_record(self):
        body = self.record_factory()
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.assertIn('_id', resp.json)

    def test_invalid_record_raises_error(self):
        body = self.invalid_record_factory()
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers,
                                  status=400)
        self.assertFormattedError(
            resp, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters", "url in body: Required")

    def test_empty_body_raises_error(self):
        resp = self.app.post(self.collection_url,
                             '',
                             headers=self.headers,
                             status=400)
        self.assertFormattedError(
            resp, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters", "url in body: Required")

    def test_invalid_uft8_raises_error(self):
        resp = self.app.post(self.collection_url,
                             '{"foo": "\\u0d1"}',
                             headers=self.headers,
                             status=400)
        self.assertFormattedError(
            resp, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters",
            "body in body: Invalid \\uXXXX escape: line 1 column 11 (char 10)")

    def test_new_records_are_linked_to_owner(self):
        body = self.record_factory()
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        record_id = resp.json['_id']
        self.db.get(self.resource, u'bob', record_id)  # not raising

    def test_get_record(self):
        url = self.item_url.format(id=self.record['_id'])
        resp = self.app.get(url, headers=self.headers)
        self.assertRecordEquals(resp.json, self.record)

    def test_get_record_unknown(self):
        url = self.item_url.format(id='unknown')
        self.app.get(url, headers=self.headers, status=404)

    def test_modify_record(self):
        url = self.item_url.format(id=self.record['_id'])
        stored = self.db.get(self.resource, u'bob', self.record['_id'])
        modified = self.modify_record(self.record)
        resp = self.app.patch_json(url, modified, headers=self.headers)
        self.assertEquals(resp.json['_id'], stored['_id'])
        self.assertRecordNotEquals(resp.json, stored)

    @mock.patch('readinglist.resource.TimeStamp.now')
    def test_modify_record_updates_timestamp(self, now_mocked):
        now_mocked.return_value = 42

        url = self.item_url.format(id=self.record['_id'])
        stored = self.db.get(self.resource, u'bob', self.record['_id'])
        before = stored['last_modified']
        modified = self.modify_record(self.record)

        resp = self.app.patch_json(url, modified, headers=self.headers)
        after = resp.json['last_modified']
        self.assertNotEquals(after, before)

    def test_modify_with_invalid_record(self):
        url = self.item_url.format(id=self.record['_id'])
        stored = self.db.get(self.resource, u'bob', self.record['_id'])
        modified = self.modify_record(self.record)
        for k in modified.keys():
            stored.pop(k)
        self.app.patch_json(url, stored, headers=self.headers, status=400)

    def test_modify_record_unknown(self):
        body = self.record_factory()
        url = self.item_url.format(id='unknown')
        self.app.patch_json(url, body, headers=self.headers, status=404)

    def test_replace_record(self):
        url = self.item_url.format(id=self.record['_id'])
        before = self.db.get(self.resource, u'bob', self.record['_id'])

        modified = self.modify_record(self.record)
        replaced = before.copy()
        replaced.update(**modified)
        resp = self.app.put_json(url, replaced, headers=self.headers)
        after = resp.json

        self.assertEquals(before['_id'], after['_id'])
        for field in modified.keys():
            self.assertEquals(replaced[field], after[field])

    def test_replace_with_invalid_record(self):
        url = self.item_url.format(id=self.record['_id'])
        body = self.invalid_record_factory()
        self.app.put_json(url, body, headers=self.headers, status=400)

    def test_replace_record_unknown(self):
        url = self.item_url.format(id='unknown')
        self.app.patch_json(url, {}, headers=self.headers, status=404)

    def test_delete_record(self):
        url = self.item_url.format(id=self.record['_id'])
        resp = self.app.delete(url, headers=self.headers)
        self.assertRecordEquals(resp.json, self.record)

    def test_delete_record_unknown(self):
        url = self.item_url.format(id='unknown')
        self.app.delete(url, headers=self.headers, status=404)


class BaseResourceAuthorizationTest(BaseWebTest):
    def test_all_views_require_authentication(self):
        record = self.record_factory()
        self.app.get(self.collection_url, status=401)
        self.app.post(self.collection_url, record, status=401)
        url = self.item_url.format(id='abc')
        self.app.get(url, status=401)
        self.app.patch(url, record, status=401)
        self.app.delete(url, status=401)

    @mock.patch('readinglist.authentication.AuthorizationPolicy.permits')
    def test_view_permissions(self, permits_mocked):
        permission_required = lambda: permits_mocked.call_args[0][-1]

        self.app.get(self.collection_url)
        self.assertEqual(permission_required(), 'readonly')

        resp = self.app.post_json(self.collection_url,
                                  self.record_factory())
        self.assertEqual(permission_required(), 'readwrite')

        url = self.item_url.format(id=resp.json['_id'])
        self.app.get(url)
        self.assertEqual(permission_required(), 'readonly')

        self.app.patch_json(url, {})
        self.assertEqual(permission_required(), 'readwrite')

        self.app.delete(url)
        self.assertEqual(permission_required(), 'readwrite')

    def test_update_record_of_another_user_will_create_it(self):
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        url = self.item_url.format(id=self.record['_id'])
        self.app.put_json(url, self.record_factory(), headers=self.headers)

    def test_cannot_modify_record_of_other_user(self):
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        url = self.item_url.format(id=self.record['_id'])
        self.app.patch_json(url, {}, headers=self.headers, status=404)

    def test_cannot_delete_record_of_other_user(self):
        self.fxa_verify.return_value = {
            'user': 'alice'
        }
        url = self.item_url.format(id=self.record['_id'])
        self.app.delete(url, headers=self.headers, status=404)


class BaseResourceTest(BaseResourceViewsTest, BaseResourceAuthorizationTest):
    pass
