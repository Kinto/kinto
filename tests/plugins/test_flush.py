import unittest

from pyramid.config import Configurator

from kinto.core.testing import get_user_headers
from kinto.events import ServerFlushed

from ..support import BaseWebTest, MINIMALIST_BUCKET, MINIMALIST_COLLECTION, MINIMALIST_RECORD


class FlushViewTest(BaseWebTest, unittest.TestCase):

    collection_url = "/buckets/beers/collections/barley/records"
    events = []

    def setUp(self):
        super().setUp()

        del self.events[:]

        bucket = {**MINIMALIST_BUCKET}

        self.alice_headers = {**self.headers, **get_user_headers("alice")}

        resp = self.app.get("/", headers=self.alice_headers)
        alice_principal = resp.json["user"]["id"]
        bucket["permissions"] = {"write": [alice_principal]}

        # Create shared bucket.
        self.app.put_json("/buckets/beers", bucket, headers=self.headers)
        self.app.put_json(
            "/buckets/beers/collections/barley", MINIMALIST_COLLECTION, headers=self.headers
        )

        # Records for alice and bob.
        self.app.post_json(
            self.collection_url, MINIMALIST_RECORD, headers=self.headers, status=201
        )
        self.app.post_json(
            self.collection_url, MINIMALIST_RECORD, headers=self.alice_headers, status=201
        )

    def tearDown(self):
        del self.events[:]
        super().tearDown()

    @classmethod
    def make_app(cls, settings=None, config=None):
        settings = cls.get_app_settings(settings)
        config = Configurator(settings=settings)
        config.add_subscriber(cls.listener, ServerFlushed)
        config.commit()
        return super().make_app(settings=settings, config=config)

    @classmethod
    def get_app_settings(cls, extras=None):
        if extras is None:
            extras = {}
        extras.setdefault("includes", "kinto.plugins.flush")
        settings = super().get_app_settings(extras)
        return settings

    @classmethod
    def listener(cls, event):
        cls.events.append(event)

    def test_returns_404_if_not_enabled_in_configuration(self):
        app = self.make_app(settings={"includes": ""})
        app.post("/__flush__", headers=self.headers, status=404)

    def test_removes_every_records_of_everykind(self):
        self.app.get(self.collection_url, headers=self.headers)
        self.app.get(self.collection_url, headers=self.alice_headers)

        self.app.post("/__flush__", headers=self.headers, status=202)

        self.app.get(self.collection_url, headers=self.headers, status=403)
        self.app.get(self.collection_url, headers=self.alice_headers, status=403)

    def test_event_triggered_post(self):
        self.app.get(self.collection_url, headers=self.headers)
        self.app.get(self.collection_url, headers=self.alice_headers)
        self.app.post("/__flush__", headers=self.headers, status=202)
        self.assertEqual(len(self.events), 1)
        self.assertTrue(isinstance(self.events[0], ServerFlushed))

    def test_flush_returns_json(self):
        response = self.app.post("/__flush__", headers=self.headers, status=202)
        self.assertEqual(response.json, {})

    def test_flush_capability_if_enabled(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("flush_endpoint", capabilities)
        expected = {
            "description": "The __flush__ endpoint can be used to remove "
            "all data from all backends.",
            "url": "https://kinto.readthedocs.io/en/latest/api/1.x/flush.html",
        }
        self.assertEqual(expected, capabilities["flush_endpoint"])
