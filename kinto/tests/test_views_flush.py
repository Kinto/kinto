import webtest
from pyramid.config import Configurator

from kinto.tests.core import support as core_support
from kinto import main
from kinto.events import ServerFlushed

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_BUCKET, MINIMALIST_COLLECTION,
                      MINIMALIST_RECORD)


class FlushViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/collections/barley/records'

    def setUp(self):
        super(FlushViewTest, self).setUp()

        self.events = []

        bucket = MINIMALIST_BUCKET.copy()

        self.alice_headers = self.headers.copy()
        self.alice_headers.update(**get_user_headers('alice'))
        alice_principal = ('basicauth:8df4b22019cc89d0bb679bc51373a9da56a'
                           '7ae9978c52fbe684510c3d257c855')
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

    def tearDown(self):
        self.events = []
        super(FlushViewTest, self).tearDown()

    def _get_test_app(self, settings=None):
        app_settings = self.get_app_settings(settings)
        self.config = Configurator(settings=app_settings)
        self.config.add_subscriber(self.listener, ServerFlushed)
        self.config.commit()
        app = webtest.TestApp(main({}, config=self.config, **app_settings))
        app.RequestClass = core_support.get_request_class(prefix="v1")

        return app

    def get_app_settings(self, extra=None):
        if extra is None:
            extra = {}
        extra.setdefault('kinto.flush_endpoint_enabled', True)
        settings = super(FlushViewTest, self).get_app_settings(extra)
        return settings

    def listener(self, event):
        self.events.append(event)

    def test_returns_404_if_not_enabled_in_configuration(self):
        extra = {'kinto.flush_endpoint_enabled': False}
        app = self._get_test_app(settings=extra)
        app.post('/__flush__', headers=self.headers, status=404)

    def test_removes_every_records_of_everykind(self):
        self.app.get(self.collection_url, headers=self.headers)
        self.app.get(self.collection_url, headers=self.alice_headers)

        self.app.post('/__flush__', headers=self.headers, status=202)

        self.app.get(self.collection_url, headers=self.headers, status=403)
        self.app.get(self.collection_url,
                     headers=self.alice_headers,
                     status=403)

    def test_event_triggered_post(self):
        self.app.get(self.collection_url, headers=self.headers)
        self.app.get(self.collection_url, headers=self.alice_headers)
        self.app.post('/__flush__', headers=self.headers, status=202)
        self.assertEqual(len(self.events), 1)
        self.assertTrue(isinstance(self.events[0], ServerFlushed))
