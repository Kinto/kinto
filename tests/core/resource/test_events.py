import mock
import uuid
from contextlib import contextmanager

from pyramid.config import Configurator

from kinto.core import statsd
from kinto.core.events import (ResourceChanged, AfterResourceChanged,
                               ResourceRead, AfterResourceRead, ACTIONS)
from kinto.core.storage.exceptions import BackendError
from kinto.core.testing import unittest

from ..support import BaseWebTest


@contextmanager
def notif_broken(app, event_cls):
    old = app.registry.notify

    def buggy(event):
        if not isinstance(event, event_cls):
            return old(event)
        raise Exception("boom")

    app.registry.notify = buggy
    yield
    app.registry.notify = old


class BaseEventTest(BaseWebTest):

    subscribed = tuple()
    events = []

    def setUp(self):
        super().setUp()
        del self.events[:]
        self.body = {'data': {'name': 'de Paris'}}

    def tearDown(self):
        del self.events[:]
        super().tearDown()

    @classmethod
    def listener(cls, event):
        cls.events.append(event)

    @classmethod
    def make_app(cls, settings=None, config=None):
        settings = cls.get_app_settings(settings)
        config = Configurator(settings=settings)
        for event_cls in cls.subscribed:
            config.add_subscriber(cls.listener, event_cls)
        config.commit()
        return super().make_app(settings=settings, config=config)


class ResourceReadTest(BaseEventTest, unittest.TestCase):

    subscribed = (ResourceRead,)

    def test_get_sends_read_event(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers, status=201)
        record_id = resp.json['data']['id']
        record_url = self.get_item_url(record_id)
        self.app.get(record_url, headers=self.headers)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'], ACTIONS.READ.value)
        self.assertEqual(len(self.events[0].read_records), 1)

    def test_collection_get_sends_read_event(self):
        self.app.get(self.collection_url, headers=self.headers)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'], ACTIONS.READ.value)
        self.assertEqual(len(self.events[0].read_records), 0)

    def test_post_sends_read_if_id_already_exists(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers, status=201)
        record = resp.json['data']
        body = {**self.body}
        body['data']['id'] = record['id']

        # a second post with the same record id
        self.app.post_json(self.collection_url, body, headers=self.headers,
                           status=200)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'], ACTIONS.READ.value)


class ResourceChangedTest(BaseEventTest, unittest.TestCase):

    subscribed = (ResourceChanged,)

    def test_events_have_custom_representation(self):
        self.app.post_json(self.collection_url, self.body,
                           headers=self.headers, status=201)
        self.assertEqual(repr(self.events[0]),
                         "<ResourceChanged action=create "
                         "uri={}>".format(self.collection_url))

    def test_post_sends_create_action(self):
        self.app.post_json(self.collection_url, self.body,
                           headers=self.headers, status=201)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)

    def test_put_sends_create_action(self):
        body = {**self.body}
        body['data']['id'] = record_id = str(uuid.uuid4())
        record_url = self.get_item_url(record_id)
        self.app.put_json(record_url, body,
                          headers=self.headers, status=201)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)

    def test_not_triggered_on_failed_put(self):
        body = {**self.body}
        body['data']['id'] = record_id = str(uuid.uuid4())
        record_url = self.get_item_url(record_id)
        self.app.put_json(record_url, body, headers=self.headers)
        headers = {**self.headers, 'If-Match': '"12345"'}
        self.app.put_json(record_url, body, headers=headers, status=412)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)

    def test_patch_sends_update_action(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers, status=201)
        record = resp.json['data']
        record_url = self.get_item_url(record['id'])

        self.app.patch_json(record_url, self.body, headers=self.headers,
                            status=200)
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)
        self.assertEqual(self.events[1].payload['action'],
                         ACTIONS.UPDATE.value)

    def test_put_sends_update_action_if_record_exists(self):
        body = {**self.body}
        body['data']['id'] = record_id = str(uuid.uuid4())
        record_url = self.get_item_url(record_id)
        self.app.put_json(record_url, body,
                          headers=self.headers, status=201)

        body['data']['more'] = 'stuff'
        self.app.put_json(record_url, body,
                          headers=self.headers, status=200)

        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)
        self.assertEqual(self.events[1].payload['action'],
                         ACTIONS.UPDATE.value)

    def test_delete_sends_delete_action(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers, status=201)
        record = resp.json['data']
        record_url = self.get_item_url(record['id'])

        self.app.delete(record_url, headers=self.headers, status=200)
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)
        self.assertEqual(self.events[1].payload['action'],
                         ACTIONS.DELETE.value)

    def test_collection_delete_sends_delete_action(self):
        self.app.post_json(self.collection_url, self.body,
                           headers=self.headers, status=201)
        self.app.post_json(self.collection_url, self.body,
                           headers=self.headers, status=201)

        self.app.delete(self.collection_url, headers=self.headers, status=200)

        self.assertEqual(len(self.events), 3)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)
        self.assertEqual(self.events[1].payload['action'],
                         ACTIONS.CREATE.value)
        self.assertEqual(self.events[2].payload['action'],
                         ACTIONS.DELETE.value)

    def test_request_fails_if_notify_fails(self):
        with notif_broken(self.app.app, ResourceChanged):
            self.app.post_json(self.collection_url, self.body,
                               headers=self.headers, status=500)
        self.assertEqual(len(self.events), 0)

    def test_triggered_on_protected_resource(self):
        app = self.make_app(settings={
            'psilo_write_principals': 'system.Authenticated'
        })
        app.post_json('/psilos', self.body,
                      headers=self.headers, status=201)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].payload['action'],
                         ACTIONS.CREATE.value)

    def test_permissions_are_stripped_from_event_on_protected_resource(self):
        app = self.make_app(settings={
            'psilo_write_principals': 'system.Authenticated'
        })
        resp = app.post_json('/psilos', self.body,
                             headers=self.headers, status=201)
        record = resp.json['data']
        record_url = '/psilos/{}'.format(record['id'])
        app.patch_json(record_url, {"data": {"name": "De barcelona"}},
                       headers=self.headers)
        impacted_records = self.events[-1].impacted_records
        self.assertNotIn('__permissions__', impacted_records[0]['new'])
        self.assertNotIn('__permissions__', impacted_records[0]['old'])


class AfterResourceChangedTest(BaseEventTest, unittest.TestCase):

    subscribed = (AfterResourceChanged,)

    def test_request_succeeds_if_notify_fails(self):
        with notif_broken(self.app.app, AfterResourceChanged):
            self.app.post_json(self.collection_url, self.body,
                               headers=self.headers)

        self.assertEqual(len(self.events), 0)


class AfterResourceReadTest(BaseEventTest, unittest.TestCase):

    subscribed = (AfterResourceRead,)

    def test_request_succeeds_if_notify_fails(self):
        with notif_broken(self.app.app, AfterResourceChanged):
            self.app.post_json(self.collection_url, self.body,
                               headers=self.headers)

        self.assertEqual(len(self.events), 0)


class ImpactedRecordsTest(BaseEventTest, unittest.TestCase):

    subscribed = (ResourceChanged,)

    def test_create_has_new_record_and_no_old_in_payload(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers)
        record = resp.json['data']
        impacted_records = self.events[-1].impacted_records
        self.assertEqual(len(impacted_records), 1)
        self.assertNotIn('old', impacted_records[0])
        self.assertEqual(impacted_records[0]['new'], record)

    def test_collection_delete_has_old_and_new_in_payload(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers)
        record1 = resp.json['data']
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers)
        record2 = resp.json['data']

        self.app.delete(self.collection_url, headers=self.headers, status=200)

        impacted_records = self.events[-1].impacted_records
        self.assertEqual(len(impacted_records), 2)
        impacted_records = sorted(impacted_records,
                                  key=lambda x: x['old']['last_modified'])
        self.assertEqual(impacted_records[0]['old'], record1)
        self.assertEqual(impacted_records[1]['old'], record2)
        self.assertEqual(impacted_records[0]['new']['deleted'], True)
        self.assertEqual(impacted_records[1]['new']['deleted'], True)
        self.assertEqual(impacted_records[0]['old']['id'],
                         impacted_records[0]['new']['id'])
        self.assertEqual(impacted_records[1]['old']['id'],
                         impacted_records[1]['new']['id'])
        deleted_ids = {impacted_records[0]['new']['id'],
                       impacted_records[1]['new']['id']}
        self.assertEqual(deleted_ids, {record1['id'], record2['id']})

    def test_update_has_old_and_new_record(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers, status=201)
        record = resp.json['data']
        record_url = self.get_item_url(record['id'])
        self.app.patch_json(record_url, {'data': {'name': 'en boite'}},
                            headers=self.headers)
        impacted_records = self.events[-1].impacted_records
        self.assertEqual(len(impacted_records), 1)
        self.assertEqual(impacted_records[0]['new']['id'], record['id'])
        self.assertEqual(impacted_records[0]['new']['id'],
                         impacted_records[0]['old']['id'])
        self.assertEqual(impacted_records[0]['old']['name'], 'de Paris')
        self.assertEqual(impacted_records[0]['new']['name'], 'en boite')

    def test_delete_has_old_and_new_record_in_payload(self):
        resp = self.app.post_json(self.collection_url, self.body,
                                  headers=self.headers, status=201)
        record = resp.json['data']
        record_url = self.get_item_url(record['id'])
        self.app.delete(record_url, headers=self.headers, status=200)

        impacted_records = self.events[-1].impacted_records
        self.assertEqual(len(impacted_records), 1)
        self.assertEqual(impacted_records[0]['old'], record)
        self.assertEqual(impacted_records[0]['new']['id'], record['id'])
        self.assertEqual(impacted_records[0]['new']['deleted'], True)


class BatchEventsTest(BaseEventTest, unittest.TestCase):

    subscribed = (ResourceChanged, ResourceRead)

    def test_impacted_records_are_merged(self):
        record_id = str(uuid.uuid4())
        record_url = self.get_item_url(record_id)
        body = {
            "defaults": {
                "method": "PUT",
                "path": record_url
            },
            "requests": [
                {"body": {'data': {'name': 'foo'}}},
                {"body": {'data': {'name': 'bar'}}},
                {"body": {'data': {'name': 'baz'}}},
                {"method": "DELETE"}
            ]
        }
        self.app.post_json("/batch", body, headers=self.headers)
        self.assertEqual(len(self.events), 3)

        create_event = self.events[0]
        self.assertEqual(create_event.payload['action'], 'create')
        self.assertEqual(len(create_event.impacted_records), 1)
        self.assertNotIn('old', create_event.impacted_records[0])
        update_event = self.events[1]
        self.assertEqual(update_event.payload['action'], 'update')
        impacted = update_event.impacted_records
        self.assertEqual(len(impacted), 2)
        self.assertEqual(impacted[0]['old']['name'], 'foo')
        self.assertEqual(impacted[0]['new']['name'], 'bar')
        self.assertEqual(impacted[1]['old']['name'], 'bar')
        self.assertEqual(impacted[1]['new']['name'], 'baz')
        delete_event = self.events[2]
        self.assertEqual(delete_event.payload['action'], 'delete')
        self.assertEqual(len(delete_event.impacted_records), 1)
        self.assertIn('old', delete_event.impacted_records[0])
        self.assertIn('new', delete_event.impacted_records[0])

    def test_one_event_is_sent_per_resource(self):
        body = {
            "defaults": {
                "method": "POST",
                "body": self.body,
            },
            "requests": [
                {"path": '/mushrooms'},
                {"path": '/mushrooms'},
                {"path": '/psilos'},
            ]
        }
        self.app.post_json("/batch", body, headers=self.headers)
        self.assertEqual(len(self.events), 2)

    def test_one_event_is_sent_per_parent_id(self):
        # /mushrooms is a UserResource (see testapp.views), which means
        # that parent_id depends on the authenticated user.
        body = {
            "defaults": {
                "path": '/mushrooms',
                "method": "POST",
                "body": self.body
            },
            "requests": [
                {"headers": {"Authorization": "Basic bWF0OjE="}},
                {"headers": {"Authorization": "Basic dG90bzp0dXR1"}},
                {"headers": {"Authorization": "Basic bWF0OjE="}},
            ]
        }
        self.app.post_json("/batch", body, headers=self.headers)
        # Two different auth headers, thus two different parent_id:
        self.assertEqual(len(self.events), 2)

    def test_one_event_is_sent_per_action(self):
        body = {
            "defaults": {
                "path": '/mushrooms',
            },
            "requests": [
                {"method": "POST", "body": self.body},
                {"method": "DELETE"},
                {"method": "GET"},
            ]
        }
        self.app.post_json("/batch", body, headers=self.headers)
        self.assertEqual(len(self.events), 3)

    def test_events_are_not_sent_if_subrequest_fails(self):
        patch = mock.patch.object(self.storage,
                                  'delete_all',
                                  side_effect=BackendError('boom'))
        patch.start()
        self.addCleanup(patch.stop)
        request_create = {
            "method": "POST",
            "body": self.body,
        }
        request_delete_all = {
            "method": "DELETE",
            "body": self.body,
        }
        body = {
            "defaults": {
                "path": self.collection_url
            },
            "requests": [request_create, request_delete_all]
        }
        self.app.post_json("/batch", body, headers=self.headers,
                           status=503)
        self.assertEqual(len(self.events), 0)


def load_from_config(config, prefix):
    class ClassListener:
        def __call__(self, event):
            pass
    return ClassListener()


@unittest.skipIf(not statsd.statsd_module, "statsd is not installed.")
class StatsDTest(BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, *args, **kwargs):
        settings = super().get_app_settings(*args, **kwargs)
        if not statsd.statsd_module:
            return settings

        settings['statsd_url'] = 'udp://localhost:8125'
        this_module = 'tests.core.resource.test_events'
        settings['event_listeners'] = 'test'
        settings['event_listeners.test.use'] = this_module
        return settings

    def test_statds_tracks_listeners_execution_duration(self):
        statsd_client = self.app.app.registry.statsd._client
        with mock.patch.object(statsd_client, 'timing') as mocked:
            self.app.post_json(self.collection_url,
                               {"data": {"name": "pouet"}},
                               headers=self.headers)
            timers = set(c[0][0] for c in mocked.call_args_list)
            self.assertIn('listeners.test', timers)
