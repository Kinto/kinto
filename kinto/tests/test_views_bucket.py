from __future__ import unicode_literals
from .support import BaseWebTest, unittest, get_user_headers

URL_PREFIX = 'http://localhost/v0'
BUCKETS_URL = '/buckets'
BUCKET_URL = '/buckets/fxa_bob'


class MethodsTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(MethodsTest, self).setUp()

    def test_get_buckets_retrieves_current_bucket_list(self):
        headers = get_user_headers("alice")
        headers.update(self.headers)
        resp = self.app.get(BUCKETS_URL, headers=headers)
        self.assertDictEqual(resp.json, {
            'links': {
                'self': '%s%s' % (URL_PREFIX, BUCKETS_URL)
            },
            'data': [{
                'type': 'bucket',
                'id': '/buckets/fxa_bob'
            }]
        })
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

    def test_get_bucket_retrieves_current_bucket(self):
        headers = get_user_headers("alice")
        headers.update(self.headers)
        resp = self.app.get(BUCKET_URL, headers=headers)
        self.assertDictEqual(resp.json, {
            'links': {
                'self': '%s%s' % (URL_PREFIX, BUCKET_URL),
                'related': '%s%s/collections' % (URL_PREFIX, BUCKET_URL)
            },
            'data': {
                'type': 'bucket',
                'id': '/buckets/fxa_bob',
                'permissions': {
                    'write': [],  # XXX: ['fxa_bob'],
                    'read': [],
                    'collections:create': [],
                    'groups:create': []
                }
            }
        })
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
