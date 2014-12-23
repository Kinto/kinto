import base64

import webtest

from readinglist import API_VERSION


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

        auth_password = base64.b64encode('bob:secret')
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic {0}'.format(auth_password),
        }

    def tearDown(self):
        self.db.flush()


class BaseResourceViewsTest(BaseWebTest):
    resource = ''

    def setUp(self):
        super(BaseResourceViewsTest, self).setUp()
        self.record = self.record_factory()
        self.db.create(self.resource, u'bob', self.record)
        self.collection_url = '/%ss' % self.resource
        self.item_url = '/%ss/{}' % self.resource

    def assertRecordEquals(self, record1, record2):
        return self.assertEqual(record1, record2)

    def assertRecordNotEquals(self, record1, record2):
        return self.assertNotEqual(record1, record2)

    def record_factory(self):
        raise NotImplementedError

    def modify_record(self, original):
        raise NotImplementedError

    def test_list(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['_items']
        self.assertEquals(len(records), 1)
        self.assertRecordEquals(records[0], self.record)

    def test_list_is_filtered_by_user(self):
        auth_password = base64.b64encode('alice:secret')
        self.headers['Authorization'] = 'Basic {}'.format(auth_password)
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['_items']
        self.assertEquals(len(records), 0)

    def test_create_record(self):
        body = self.record_factory()
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        self.assertIn('_id', resp.json)

    def test_new_records_are_linked_to_owner(self):
        body = self.record_factory()
        resp = self.app.post_json(self.collection_url,
                                  body,
                                  headers=self.headers)
        record_id = resp.json['_id']
        self.db.get(self.resource, u'bob', record_id)  # not raising

    def test_get_record(self):
        url = self.item_url.format(self.record['_id'])
        resp = self.app.get(url, headers=self.headers)
        self.assertRecordEquals(resp.json, self.record)

    def test_get_record_unknown(self):
        url = self.item_url.format('unknown')
        self.app.get(url, headers=self.headers, status=404)

    def test_modify_record(self):
        url = self.item_url.format(self.record['_id'])
        stored = self.db.get(self.resource, u'bob', self.record['_id'])
        modified = self.modify_record(self.record)
        resp = self.app.patch_json(url, modified, headers=self.headers)
        self.assertEquals(resp.json['_id'], stored['_id'])
        self.assertRecordNotEquals(resp.json, stored)

    def test_modify_record_unknown(self):
        url = self.item_url.format('unknown')
        self.app.patch_json(url, {}, headers=self.headers, status=404)

    def test_delete_record(self):
        url = self.item_url.format(self.record['_id'])
        resp = self.app.delete(url, headers=self.headers)
        self.assertRecordEquals(resp.json, self.record)

    def test_delete_record_unknown(self):
        url = self.item_url.format('unknown')
        self.app.delete(url, headers=self.headers, status=404)


class BaseResourceAuthorizationTest(BaseWebTest):
    resource = ''

    def test_all_views_require_authentication(self):
        self.app.get(self.collection_url, status=403)
        self.app.post(self.collection_url, {}, status=403)
        url = self.item_url.format('abc')
        self.app.get(url, status=403)
        self.app.patch(url, {}, status=403)
        self.app.delete(url, status=403)


class BaseResourceTest(BaseResourceViewsTest, BaseResourceAuthorizationTest):
    pass
