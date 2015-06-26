from cliquet.tests.support import authorize

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_COLLECTION,
                      MINIMALIST_RECORD)


class FlushViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'

    @authorize(authz_class='kinto.tests.support.AllowAuthorizationPolicy')
    def setUp(self):
        super(FlushViewTest, self).setUp()

        bucket = MINIMALIST_BUCKET.copy()

        self.alice_headers = self.headers.copy()
        self.alice_headers.update(**get_user_headers('alice'))
        alice_principal = ('basicauth:d5b0026601f1b251974e09548d44155e16812'
                           'e3c64ff7ae053fe3542e2ca1570')
        bucket['permissions'] = {'write': [alice_principal]}

        # Create shared bucket.
        self.app.put_json('/buckets/beers', bucket,
                          headers=self.headers)
        self.app.put_json('/buckets/beers/collections/barley',
                          MINIMALIST_COLLECTION,
                          headers=self.headers)

        # Records for alice and bob.
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.headers,
                           status=201)
        self.app.post_json(self.collection_url,
                           MINIMALIST_RECORD,
                           headers=self.alice_headers,
                           status=201)

    def get_app_settings(self, extra=None):
        if extra is None:
            extra = {}
        extra.setdefault('kinto.flush_endpoint_enabled', True)
        settings = super(FlushViewTest, self).get_app_settings(extra)
        return settings

    def test_returns_404_if_not_enabled_in_configuration(self):
        extra = {'kinto.flush_endpoint_enabled': False}
        app = self._get_test_app(settings=extra)
        app.post('/__flush__', headers=self.headers, status=404)

    def test_removes_every_records_of_everykind(self):
        self.app.post('/__flush__', headers=self.headers, status=202)

        self.app.get(self.collection_url, headers=self.headers, status=404)
        self.app.get(self.collection_url,
                     headers=self.alice_headers,
                     status=404)
