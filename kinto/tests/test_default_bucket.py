from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_RECORD)


class DefaultBucketViewTest(BaseWebTest, unittest.TestCase):

    bucket_url = '/buckets/default'
    collection_url = '/buckets/default/collections/tasks'

    def setUp(self):
        super(DefaultBucketViewTest, self).setUp()

    def test_default_bucket_exists_and_has_user_id(self):
        bucket = self.app.get(self.bucket_url, headers=self.headers)

        expected_bucket = MINIMALIST_BUCKET.copy()
        expected_bucket['data']['id'] = self.principal
        expected_bucket['data']['last_modified'] = self.storage \
            .collection_timestamp(self.principal, None)
        expected_bucket['permissions'] = {'write': [self.principal]}

        self.assertDictEqual(bucket.json, expected_bucket)

    def test_default_bucket_collections_are_automatically_created(self):
        self.app.get(self.collection_url, headers=self.headers, status=200)

    def test_adding_a_task_for_bob_doesnt_add_it_for_alice(self):
        record = MINIMALIST_RECORD.copy()
        resp = self.app.post_json(self.collection_url + '/records',
                                  record, headers=get_user_headers('bob'))
        record_id = self.collection_url + '/records/' + resp.json['data']['id']
        resp = self.app.get(record_id, record,
                            headers=get_user_headers('alice'), status=404)
