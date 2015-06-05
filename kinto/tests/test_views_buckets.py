from .support import BaseWebTest, unittest, get_user_headers


MINIMALIST_ITEM = dict()


class BucketViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets'
    record_url = '/buckets/beers'

    def test_buckets_do_not_support_post(self):
        self.app.post(self.collection_url, headers=self.headers,
                      status=405)

    def test_buckets_can_be_put_with_simple_name(self):
        response = self.app.put_json(self.record_url,
                                     MINIMALIST_ITEM,
                                     headers=self.headers)
        self.assertEqual(response.json['id'], 'beers')

    def test_buckets_name_should_be_simple(self):
        self.app.put_json('/buckets/__beers__',
                          MINIMALIST_ITEM,
                          headers=self.headers,
                          status=400)
