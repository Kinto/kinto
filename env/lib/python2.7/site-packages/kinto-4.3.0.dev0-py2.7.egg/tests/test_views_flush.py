import os
import unittest

from pyramid.config import Configurator

from kinto.core.testing import get_user_headers
from kinto.events import ServerFlushed

from .support import (BaseWebTest,
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

        resp = self.app.get('/', headers=self.alice_headers)
        alice_principal = resp.json['user']['id']
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

    def make_app(self, settings=None, config=None):
        settings = self.get_app_settings(settings)
        config = Configurator(settings=settings)
        config.add_subscriber(self.listener, ServerFlushed)
        config.commit()
        return super(FlushViewTest, self).make_app(settings=settings,
                                                   config=config)

    def get_app_settings(self, extras=None):
        if extras is None:
            extras = {}
        extras.setdefault('flush_endpoint_enabled', True)
        settings = super(FlushViewTest, self).get_app_settings(extras)
        return settings

    def listener(self, event):
        self.events.append(event)

    def test_returns_404_if_not_enabled_in_configuration(self):
        extra = {'flush_endpoint_enabled': False}
        app = self.make_app(settings=extra)
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

    def test_can_be_enabled_via_environment(self):
        os.environ['KINTO_FLUSH_ENDPOINT_ENABLED'] = 'true'
        extra = {'flush_endpoint_enabled': False}
        app = self.make_app(settings=extra)
        app.post('/__flush__', headers=self.headers)
        os.environ.pop('KINTO_FLUSH_ENDPOINT_ENABLED')
