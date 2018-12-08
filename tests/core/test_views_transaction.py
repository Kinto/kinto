import time
import threading
import unittest
from uuid import uuid4
from unittest import mock

from pyramid import testing
from pyramid import httpexceptions

from kinto.core.storage.exceptions import BackendError
from kinto.core.utils import sqlalchemy
from kinto.core import events
from kinto.core.testing import skip_if_no_postgresql

from .support import PostgreSQLTest, USER_PRINCIPAL


@skip_if_no_postgresql
class TransactionTest(PostgreSQLTest, unittest.TestCase):
    def test_heartbeat_releases_transaction_lock(self):
        for i in range(4):
            # 4 calls because we have 3 backends
            # See bug Kinto/kinto#804
            self.app.get("/__heartbeat__")

    def test_storage_operations_are_committed_on_success(self):
        request_create = {
            "method": "POST",
            "path": "/mushrooms",
            "body": {"data": {"name": "Trompette de la mort"}},
        }
        body = {"requests": [request_create, request_create, request_create]}
        self.app.post_json("/batch", body, headers=self.headers)
        resp = self.app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 3)

    def test_transaction_isolation_within_request(self):
        request_create = {
            "method": "POST",
            "path": "/mushrooms",
            "body": {"data": {"name": "Vesse de loup"}},
        }
        request_get = {"method": "GET", "path": "/mushrooms"}
        body = {"requests": [request_create, request_get]}
        resp = self.app.post_json("/batch", body, headers=self.headers)
        self.assertEqual(resp.json["responses"][1]["body"]["data"][0]["name"], "Vesse de loup")

    def test_modifications_are_rolled_back_on_error(self):
        self.run_failing_batch()

        resp = self.app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 0)

    def test_modifications_are_not_rolled_back_on_401_error(self):
        request_create = {
            "method": "POST",
            "path": "/mushrooms",
            "body": {"data": {"name": "Vesse de loup"}},
        }
        request_get = {"method": "GET", "path": "/this-is-an-unknown-url"}
        body = {"requests": [request_create, request_get]}
        resp = self.app.post_json("/batch", body, headers=self.headers)
        resp = self.app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 1)

    def test_modifications_are_rolled_back_on_409_error(self):
        bucket_create = {
            "method": "POST",
            "path": "/mushrooms",
            "body": {"data": {"name": "Vesse de loup", "last_modified": 123}},
        }
        bucket_ccreate = {
            "method": "POST",
            "path": "/mushrooms",
            "body": {"data": {"name": "Vesse de loup", "last_modified": 123}},
        }
        body = {"requests": [bucket_create, bucket_ccreate]}
        resp = self.app.post_json("/batch", body, headers=self.headers)
        response = resp.json["responses"][1]
        self.assertEqual(response["status"], 409)
        resp = self.app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 0)

    def test_modifications_are_rolled_back_on_error_accross_backends(self):
        self.run_failing_post()

        resp = self.app.get("/psilos", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 0)


class IntegrityConstraintTest(PostgreSQLTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        if sqlalchemy is not None:
            settings.pop("storage_poolclass", None)  # Use real pool.
        return settings

    def test_concurrent_transactions_do_not_fail(self):
        # This test originally intended to reproduce integrity errors and check
        # that a 409 was obtained. But since every errors that could be reproduced
        # could be also be fixed, this test just asserts that API responses
        # are consistent. # See Kinto/kinto#1125.

        # Make requests slow.
        patch = mock.patch(
            "kinto.core.resource.Resource.postprocess",
            lambda s, r, a="read", old=None: time.sleep(0.2) or {},
        )
        patch.start()
        self.addCleanup(patch.stop)

        # Same object created in two concurrent requests.
        body = {"data": {"id": str(uuid4())}}
        results = set()

        def create_object():
            r = self.app.post_json("/psilos", body, headers=self.headers, status=(201, 200, 409))
            results.add(r.status_code)

        thread1 = threading.Thread(target=create_object)
        thread2 = threading.Thread(target=create_object)
        thread1.start()
        time.sleep(0.1)
        thread2.start()
        thread1.join()
        thread2.join()
        self.assertTrue({201, 200, 409} >= results)


@skip_if_no_postgresql
class TransactionCacheTest(PostgreSQLTest, unittest.TestCase):
    def setUp(self):
        def cache_and_fails(this, *args, **kwargs):
            self.cache.set("test-cache", "a value", ttl=100)
            raise BackendError("boom")

        patch = mock.patch.object(self.permission, "add_principal_to_ace", wraps=cache_and_fails)
        self.addCleanup(patch.stop)
        patch.start()

    def test_cache_backend_operations_are_always_committed(self):
        self.app.post_json(
            "/psilos", {"data": {"name": "Amanite"}}, headers=self.headers, status=503
        )

        # Storage was rolled back.
        resp = self.app.get("/psilos", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 0)

        # Cache was committed.
        self.assertEqual(self.cache.get("test-cache"), "a value")


@skip_if_no_postgresql
class TransactionEventsTest(PostgreSQLTest, unittest.TestCase):
    def make_app_with_subscribers(self, subscribers):
        settings = self.get_app_settings({})
        config = testing.setUp(settings=settings)
        for event, subscriber in subscribers:
            config.add_subscriber(subscriber, event)
        config.commit()
        return self.make_app(config=config)

    def send_batch_create(self, app, **kwargs):
        body = {
            "defaults": {"method": "POST", "body": {"data": {"name": "Vesse de loup"}}},
            "requests": [{"path": "/mushrooms"}, {"path": "/mushrooms"}],
        }
        return app.post_json("/batch", body, headers=self.headers, **kwargs)

    def test_resourcechanged_is_executed_within_transaction(self):
        def store_object(event):
            storage = event.request.registry.storage
            extra_object = {"id": "3.14", "z": 42}
            storage.create("mushroom", USER_PRINCIPAL, extra_object)

        app = self.make_app_with_subscribers([(events.ResourceChanged, store_object)])
        self.send_batch_create(app)
        resp = app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 2 + 1)

    def test_resourcechanged_is_rolledback_with_transaction(self):
        def store_object(event):
            storage = event.request.registry.storage
            extra_object = {"id": "3.14", "z": 42}
            storage.create("mushroom", USER_PRINCIPAL, extra_object)

        app = self.make_app_with_subscribers([(events.ResourceChanged, store_object)])
        # We want to patch the following method so that it raises an exception,
        # to make sure the rollback is happening correctly.
        to_patch = "transaction._manager.ThreadTransactionManager.commit"
        with mock.patch(to_patch) as mocked:
            mocked.side_effect = ValueError
            self.send_batch_create(app, status=500)
        resp = app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 0)

    def test_resourcechanged_can_rollback_whole_request(self):
        def store_object(event):
            raise httpexceptions.HTTPInsufficientStorage()

        app = self.make_app_with_subscribers([(events.ResourceChanged, store_object)])
        self.send_batch_create(app, status=507)
        resp = app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 0)

    def test_afterresourcechanged_cannot_rollback_whole_request(self):
        def store_object(event):
            raise httpexceptions.HTTPInsufficientStorage()

        app = self.make_app_with_subscribers([(events.AfterResourceChanged, store_object)])
        self.send_batch_create(app, status=200)
        resp = app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 2)


@skip_if_no_postgresql
class WithoutTransactionTest(PostgreSQLTest, unittest.TestCase):
    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["transaction_per_request"] = False
        return settings

    def test_modifications_are_not_rolled_back_on_error(self):
        self.run_failing_batch()

        resp = self.app.get("/mushrooms", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 2)

    def test_modifications_are_not_rolled_back_on_error_accross_backends(self):
        self.run_failing_post()

        resp = self.app.get("/psilos", headers=self.headers)
        self.assertEqual(len(resp.json["data"]), 1)
