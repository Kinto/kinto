import mock

from pyramid import testing
from pyramid import httpexceptions

from cliquet.storage.exceptions import BackendError
from cliquet.utils import sqlalchemy
from cliquet import events
from .support import (BaseWebTest, unittest, skip_if_no_postgresql,
                      USER_PRINCIPAL)


class PostgreSQLTest(BaseWebTest):
    def setUp(self):
        super(PostgreSQLTest, self).setUp()
        self.storage.initialize_schema()
        self.permission.initialize_schema()

    def tearDown(self):
        super(BaseWebTest, self).tearDown()
        self.storage.flush()
        self.permission.flush()

    def get_app_settings(self, extras=None):
        settings = super(PostgreSQLTest, self).get_app_settings(extras)
        if sqlalchemy is not None:
            from .test_storage import PostgreSQLStorageTest
            from .test_permission import PostgreSQLPermissionTest
            settings.update(**PostgreSQLStorageTest.settings)
            settings.update(**PostgreSQLPermissionTest.settings)
            settings.pop('storage_poolclass', None)
            settings.pop('permission_poolclass', None)
        return settings

    def run_failing_batch(self):
        patch = mock.patch.object(
            self.storage,
            'delete_all',
            side_effect=BackendError('boom'))
        self.addCleanup(patch.stop)
        patch.start()
        request_create = {
            'method': 'POST',
            'path': '/mushrooms',
            'body': {'data': {'name': 'Amanite'}}
        }
        request_delete = {
            'method': 'DELETE',
            'path': '/mushrooms'
        }
        body = {'requests': [request_create, request_create, request_delete]}
        self.app.post_json('/batch', body, headers=self.headers, status=503)

    def run_failing_post(self):
        patch = mock.patch.object(
            self.permission,
            'add_principal_to_ace',
            side_effect=BackendError('boom'))
        self.addCleanup(patch.stop)
        patch.start()
        self.app.post_json('/psilos',
                           {'data': {'name': 'Amanite'}},
                           headers=self.headers,
                           status=503)


@skip_if_no_postgresql
class TransactionTest(PostgreSQLTest, unittest.TestCase):

    def test_storage_operations_are_committed_on_success(self):
        request_create = {
            'method': 'POST',
            'path': '/mushrooms',
            'body': {'data': {'name': 'Trompette de la mort'}}
        }
        body = {'requests': [request_create, request_create, request_create]}
        self.app.post_json('/batch', body, headers=self.headers)
        resp = self.app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 3)

    def test_transaction_isolation_within_request(self):
        request_create = {
            'method': 'POST',
            'path': '/mushrooms',
            'body': {'data': {'name': 'Vesse de loup'}}
        }
        request_get = {
            'method': 'GET',
            'path': '/mushrooms',
        }
        body = {'requests': [request_create, request_get]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        self.assertEqual(resp.json['responses'][1]['body']['data'][0]['name'],
                         'Vesse de loup')

    def test_modifications_are_rolled_back_on_error(self):
        self.run_failing_batch()

        resp = self.app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_modifications_are_not_rolled_back_on_4XX_error(self):
        request_create = {
            'method': 'POST',
            'path': '/mushrooms',
            'body': {'data': {'name': 'Vesse de loup'}}
        }
        request_get = {
            'method': 'GET',
            'path': '/this-is-an-unknown-url',
        }
        body = {'requests': [request_create, request_get]}
        resp = self.app.post_json('/batch', body, headers=self.headers)
        resp = self.app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)

    def test_modifications_are_rolled_back_on_error_accross_backends(self):
        self.run_failing_post()

        resp = self.app.get('/psilos', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)


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
            "defaults": {
                "method": "POST",
                "body": {'data': {'name': 'Vesse de loup'}},
            },
            "requests": [
                {"path": '/mushrooms'},
                {"path": '/mushrooms'}
            ]
        }
        return app.post_json("/batch", body, headers=self.headers, **kwargs)

    def test_resourcechanged_is_executed_within_transaction(self):
        def store_record(event):
            storage = event.request.registry.storage
            extra_record = {"id": "3.14", "z": 42}
            storage.create("mushroom", USER_PRINCIPAL, extra_record)

        app = self.make_app_with_subscribers([(events.ResourceChanged,
                                               store_record)])
        self.send_batch_create(app)
        resp = app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 2 + 1)

    def test_resourcechanged_is_rolledback_with_transaction(self):
        def store_record(event):
            storage = event.request.registry.storage
            extra_record = {"id": "3.14", "z": 42}
            storage.create("mushroom", USER_PRINCIPAL, extra_record)

        app = self.make_app_with_subscribers([(events.ResourceChanged,
                                               store_record)])
        with mock.patch('pyramid_tm.transaction.manager.commit') as mocked:
            mocked.side_effect = ValueError
            self.send_batch_create(app, status=500)
        resp = app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_resourcechanged_can_rollback_whole_request(self):
        def store_record(event):
            raise httpexceptions.HTTPInsufficientStorage()

        app = self.make_app_with_subscribers([(events.ResourceChanged,
                                               store_record)])
        self.send_batch_create(app, status=507)
        resp = app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 0)

    def test_afterresourcechanged_cannot_rollback_whole_request(self):
        def store_record(event):
            raise httpexceptions.HTTPInsufficientStorage()

        app = self.make_app_with_subscribers([(events.AfterResourceChanged,
                                               store_record)])
        self.send_batch_create(app, status=200)
        resp = app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 2)


@skip_if_no_postgresql
class WithoutTransactionTest(PostgreSQLTest, unittest.TestCase):

    def get_app_settings(self, extras=None):
        settings = super(WithoutTransactionTest, self).get_app_settings(extras)
        settings['transaction_per_request'] = False
        return settings

    def test_modifications_are_not_rolled_back_on_error(self):
        self.run_failing_batch()

        resp = self.app.get('/mushrooms', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 2)

    def test_modifications_are_not_rolled_back_on_error_accross_backends(self):
        self.run_failing_post()

        resp = self.app.get('/psilos', headers=self.headers)
        self.assertEqual(len(resp.json['data']), 1)
