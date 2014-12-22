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
        self.headers = {
            'Content-Type': 'application/json',
        }

    def tearDown(self):
        self.db.flush()


class BaseResourceTest(BaseWebTest):
    resource = ''

    def setUp(self):
        super(BaseResourceTest, self).setUp()
        self.record = self.record_factory()
        self.db.create(self.resource, '', self.record)

    def assertRecordEquals(self, record1, record2):
        return self.assertEquals(record1, record2)

    def record_factory(self):
        raise NotImplementedError

    def modify_record(self, original):
        raise NotImplementedError

    def test_list(self):
        url = '/{}s'.format(self.resource)
        resp = self.app.get(url, headers=self.headers)
        records = resp.json['_items']
        self.assertEquals(len(records), 1)
        self.assertRecordEquals(records[0], self.record)

    def test_create_record(self):
        url = '/{}s'.format(self.resource)
        body = self.record_factory()
        resp = self.app.post_json(url, body, headers=self.headers)
        self.assertIn('_id', resp.json)

    def test_get_record(self):
        url = '/{}s/{}'.format(self.resource, self.record['_id'])
        resp = self.app.get(url, headers=self.headers)
        self.assertRecordEquals(resp.json, self.record)

    def test_get_record_unknown(self):
        url = '/{}s/unknown'.format(self.resource)
        self.app.get(url, headers=self.headers, status=404)

    def test_modify_record(self):
        url = '/{}s/{}'.format(self.resource, self.record['_id'])
        modified = self.modify_record(self.record)
        resp = self.app.patch_json(url, modified, headers=self.headers)
        stored = self.db.get(self.resource, '', self.record['_id'])
        self.assertRecordEquals(resp.json, stored)

    def test_modify_record_unknown(self):
        url = '/{}s/unknown'.format(self.resource)
        self.app.patch_json(url, {}, headers=self.headers, status=404)

    def test_delete_record(self):
        url = '/{}s/{}'.format(self.resource, self.record['_id'])
        resp = self.app.delete(url, headers=self.headers)
        self.assertRecordEquals(resp.json, self.record)

    def test_delete_record_unknown(self):
        url = '/{}s/unknown'.format(self.resource)
        self.app.delete(url, headers=self.headers, status=404)
