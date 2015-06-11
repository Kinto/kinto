import mock
from cliquet.tests.support import authorize

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_COLLECTION,
                      MINIMALIST_RECORD)


@authorize(authz_class='kinto.tests.support.AllowAuthorizationPolicy')
class FlushViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'

    def setUp(self):
        super(FlushViewTest, self).setUp()

        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)

        headers = self.headers.copy()
        headers.update(**get_user_headers('bob'))
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=headers,
                           status=201)
        headers.update(**get_user_headers('alice'))
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=headers,
                           status=201)

    def test_returns_405_if_not_enabled_in_configuration(self):
        self.app.post('/__flush__', headers=self.headers, status=405)

    def test_removes_every_records_of_everykind(self):
        headers = self.headers.copy()
        with mock.patch.dict(self.app.app.registry.settings,
                             [('kinto.flush_endpoint_enabled', 'true')]):
            self.app.post('/__flush__', headers=self.headers, status=202)

        self.app.get('/buckets/beers', headers=headers, status=404)
        self.app.get(self.collection_url, headers=headers, status=404)
