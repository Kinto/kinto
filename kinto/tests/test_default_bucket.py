from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_RECORD)

from cliquet.utils import hmac_digest


class DefaultBucketViewTest(BaseWebTest, unittest.TestCase):

    bucket_url = '/buckets/default'
    collection_url = '/buckets/default/collections/tasks'

    def setUp(self):
        super(DefaultBucketViewTest, self).setUp()

    def test_default_bucket_exists_and_has_user_id(self):
        bucket = self.app.get(self.bucket_url, headers=self.headers)
        result = bucket.json
        settings = self.app.app.registry.settings
        hmac_secret = settings['cliquet.userid_hmac_secret']
        bucket_id = hmac_digest(hmac_secret, self.principal)

        self.assertEqual(result['data']['id'], bucket_id)
        self.assertEqual(result['permissions']['write'], [self.principal])

    def test_default_bucket_collections_are_automatically_created(self):
        self.app.get(self.collection_url, headers=self.headers, status=200)

    def test_adding_a_task_for_bob_doesnt_add_it_for_alice(self):
        record = MINIMALIST_RECORD.copy()
        resp = self.app.post_json(self.collection_url + '/records',
                                  record, headers=get_user_headers('bob'))
        record_id = self.collection_url + '/records/' + resp.json['data']['id']
        resp = self.app.get(record_id, headers=get_user_headers('alice'),
                            status=404)

    def test_unauthenticated_bucket_access_raises_json_401(self):
        resp = self.app.get(self.bucket_url, status=401)
        self.assertEquals(resp.json['message'],
                          'Please authenticate yourself to use this endpoint.')
