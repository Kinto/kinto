import mock
import unittest
from uuid import UUID

from pyramid.httpexceptions import HTTPBadRequest

from kinto.core.errors import ERRORS, http_error
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.testing import get_user_headers, FormattedErrorMixin
from kinto.core.utils import hmac_digest

from ..support import BaseWebTest, MINIMALIST_RECORD


class DefaultBucketWebTest(BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['includes'] = 'kinto.plugins.default_bucket'
        return settings


class DefaultBucketViewTest(FormattedErrorMixin, DefaultBucketWebTest):

    bucket_url = '/buckets/default'
    collection_url = '/buckets/default/collections/tasks'

    def test_default_bucket_exists_and_has_user_id(self):
        bucket = self.app.get(self.bucket_url, headers=self.headers)
        result = bucket.json
        settings = self.app.app.registry.settings
        hmac_secret = settings['userid_hmac_secret']
        bucket_id = hmac_digest(hmac_secret, self.principal)[:32]

        self.assertEqual(result['data']['id'], str(UUID(bucket_id)))
        self.assertEqual(result['permissions']['write'], [self.principal])

    def test_default_bucket_can_still_be_explicitly_created(self):
        bucket = {'permissions': {'read': ['system.Everyone']}}
        resp = self.app.put_json(self.bucket_url, bucket, headers=self.headers)
        result = resp.json
        self.assertIn('system.Everyone', result['permissions']['read'])

    def test_default_bucket_collection_can_still_be_explicitly_created(self):
        collection = {'data': {'synced': True}}
        resp = self.app.put_json(self.collection_url, collection, headers=self.headers)
        result = resp.json
        self.assertIn('synced', result['data'])
        self.assertTrue(result['data']['synced'])
        resp = self.app.get(self.collection_url, headers=self.headers)
        result = resp.json
        self.assertIn('synced', result['data'])
        self.assertTrue('synced', result['data']['synced'])

    def test_default_bucket_can_be_created_with_simple_put(self):
        self.app.put(self.bucket_url, headers=get_user_headers('bob'), status=201)

    def test_default_bucket_collections_are_automatically_created(self):
        self.app.get(self.collection_url, headers=self.headers, status=200)

    def test_adding_a_task_for_bob_doesnt_add_it_for_alice(self):
        record = {**MINIMALIST_RECORD}
        resp = self.app.post_json(self.collection_url + '/records',
                                  record, headers=get_user_headers('bob'))
        record_id = '{}/records/{}'.format(self.collection_url, resp.json['data']['id'])
        resp = self.app.get(record_id, headers=get_user_headers('alice'),
                            status=404)

    def test_unauthenticated_bucket_access_raises_json_401(self):
        resp = self.app.get(self.bucket_url, status=401)
        self.assertEquals(resp.json['message'],
                          'Please authenticate yourself to use this endpoint.')

    def test_bucket_id_is_an_uuid_with_dashes(self):
        bucket = self.app.get(self.bucket_url, headers=self.headers)
        bucket_id = bucket.json['data']['id']
        self.assertIn('-', bucket_id)
        try:
            UUID(bucket_id)
        except ValueError:
            self.fail('bucket_id: {} is not a valid UUID.'.format(bucket_id))

    def test_second_call_on_default_bucket_doesnt_raise_a_412(self):
        self.app.get(self.bucket_url, headers=self.headers)
        self.app.get(self.bucket_url, headers=self.headers)

    def test_second_call_on_default_bucket_collection_doesnt_raise_a_412(self):
        self.app.get(self.collection_url, headers=self.headers)
        self.app.get(self.collection_url, headers=self.headers)

    def test_querystring_parameters_are_taken_into_account(self):
        self.app.get(self.collection_url + '/records?_since=invalid',
                     headers=self.headers,
                     status=400)

    def test_option_is_possible_without_authentication_for_default(self):
        headers = 'authorization,content-type'
        self.app.options(self.collection_url + '/records',
                         headers={
                             'Origin': 'http://localhost:8000',
                             'Access-Control-Request-Method': 'GET',
                             'Access-Control-Request-Headers': headers})

    def test_cors_headers_are_provided_on_errors(self):
        resp = self.app.post_json(self.collection_url + '/records',
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        current = resp.json['data']['last_modified']
        headers = {**self.headers, 'Origin': 'http://localhost:8000',
                   'If-None-Match': ('"{}"'.format(current)).encode('utf-8')}
        resp = self.app.get(self.collection_url + '/records',
                            headers=headers, status=304)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertIn('ETag', resp.headers['Access-Control-Expose-Headers'])

    def test_etag_is_present_and_exposed_in_304_error(self):
        resp = self.app.post_json(self.collection_url + '/records',
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        current = resp.json['data']['last_modified']
        headers = {**self.headers, 'Origin': 'http://localhost:8000',
                   'If-None-Match': ('"{}"'.format(current)).encode('utf-8')}
        resp = self.app.get(self.collection_url + '/records',
                            headers=headers, status=304)
        self.assertIn('Access-Control-Expose-Headers', resp.headers)
        self.assertIn('ETag', resp.headers)
        self.assertIn('ETag', resp.headers['Access-Control-Expose-Headers'])

    def test_bucket_id_starting_with_default_can_still_be_created(self):
        # We need to create the bucket first since it is not the default bucket
        resp = self.app.put(
            self.bucket_url.replace('default', 'default-1234'),
            headers=self.headers, status=201)
        bucket_id = resp.json['data']['id']
        self.assertEquals(bucket_id, 'default-1234')

        # We can then create the collection
        collection_url = '/buckets/default-1234/collections/default'
        self.app.put(
            collection_url,
            headers=self.headers,
            status=201)
        resp = self.app.get('/buckets/default-1234/collections',
                            headers=self.headers)
        self.assertEquals(resp.json['data'][0]['id'], 'default')

    def test_bucket_id_in_body_can_be_default(self):
        self.app.put_json('/buckets/default',
                          {'data': {'id': 'default'}},
                          headers=self.headers,
                          status=201)

    def test_default_bucket_objects_are_checked_only_once_in_batch(self):
        batch = {'requests': []}
        nb_create = 25
        for i in range(nb_create):
            request = {'method': 'POST',
                       'path': self.collection_url + '/records',
                       'body': MINIMALIST_RECORD}
            batch['requests'].append(request)

        with mock.patch.object(self.storage, 'create',
                               wraps=self.storage.create) as patched:
            self.app.post_json('/batch', batch, headers=self.headers)
            self.assertEqual(patched.call_count, nb_create + 2)

    def test_parent_collection_is_taken_from_the_one_created_in_batch(self):
        batch = {'requests': []}
        nb_create = 25
        for i in range(nb_create):
            request = {'method': 'POST',
                       'path': self.collection_url + '/records',
                       'body': MINIMALIST_RECORD}
            batch['requests'].append(request)

        with mock.patch.object(self.storage, 'create',
                               wraps=self.storage.create) as patched:
            self.app.post_json('/batch', batch, headers=self.headers)
            # Called twice only: bucket + collection ids unicity.
            self.assertEqual(patched.call_count, 25 + 2)

    def test_parent_collection_is_taken_from_the_one_checked_in_batch(self):
        # Create it first.
        self.app.put(self.collection_url, headers=self.headers, status=201)

        batch = {'requests': []}
        nb_create = 25
        for i in range(nb_create):
            request = {'method': 'POST',
                       'path': self.collection_url + '/records',
                       'body': MINIMALIST_RECORD}
            batch['requests'].append(request)

        with mock.patch.object(self.storage, 'create',
                               wraps=self.storage.create) as patched:
            self.app.post_json('/batch', batch, headers=self.headers)
            # Called twice only: bucket + collection ids unicity.
            self.assertEqual(patched.call_count, 25 + 2)

    def test_collection_id_is_validated(self):
        collection_url = '/buckets/default/collections/__files__/records'
        self.app.get(collection_url, headers=self.headers, status=400)

    def test_collection_id_does_not_support_unicode(self):
        collection_url = '/buckets/default/collections/%E8%A6%8B/records'
        self.app.get(collection_url, headers=self.headers, status=400)

    def test_405_is_a_valid_formatted_error(self):
        response = self.app.post(self.collection_url,
                                 headers=self.headers, status=405)
        self.assertFormattedError(
            response, 405, ERRORS.METHOD_NOT_ALLOWED, "Method Not Allowed",
            "Method not allowed on this endpoint.")

    def test_formatted_error_are_passed_through(self):
        response = http_error(HTTPBadRequest(),
                              errno=ERRORS.INVALID_PARAMETERS,
                              message='Yop')

        with mock.patch.object(self.storage, 'create') as mocked:
            mocked.side_effect = [
                {"id": "abc", "last_modified": 43},
                {"id": "abc", "last_modified": 44},
                response
            ]
            resp = self.app.post(self.collection_url + '/records',
                                 headers=self.headers,
                                 status=400)
            self.assertEqual(resp.body, response.body)

    def test_trailing_slash_redirection_works_for_default_bucket(self):
        collection_url = '/buckets/default/'
        resp = self.app.get(collection_url, headers=self.headers, status=307)
        assert resp.headers['Location'].endswith('/buckets/default')

    def test_trailing_slash_redirection_works_for_collections(self):
        collection_url = '/buckets/default/collections/'
        resp = self.app.get(collection_url, headers=self.headers, status=307)
        assert resp.headers['Location'].endswith('/buckets/default/collections')

    def test_trailing_slash_redirection_works_for_collection(self):
        collection_url = '/buckets/default/collections/foo/'
        resp = self.app.get(collection_url, headers=self.headers, status=307)
        assert resp.headers['Location'].endswith('/buckets/default/collections/foo')

    def test_trailing_slash_redirection_works_for_records(self):
        records_url = '/buckets/default/collections/foo/records/'
        resp = self.app.get(records_url, headers=self.headers, status=307)
        assert resp.headers['Location'].endswith('/buckets/default/collections/foo/records')

    def test_trailing_slash_redirection_works_for_record(self):
        records_url = '/buckets/default/collections/foo/records/bar/'
        resp = self.app.get(records_url, headers=self.headers, status=307)
        assert resp.headers['Location'].endswith('/buckets/default/collections/foo/records/bar')


class HelloViewTest(DefaultBucketWebTest):

    def test_returns_bucket_id_and_url_if_authenticated(self):
        response = self.app.get('/', headers=self.headers)
        self.assertEqual(response.json['user']['bucket'],
                         'ddaf8694-fa9e-2949-ed0e-77198a7907fb')

    def test_flush_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('default_bucket', capabilities)


_events = []


def load_from_config(config, prefix):
    def listener(event):
        _events.append(event)

    return listener


class EventsTest(DefaultBucketWebTest):
    def tearDown(self):
        super().tearDown()
        del _events[:]

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings = {**settings, 'event_listeners': 'testevent',
                    'event_listeners.testevent.use': 'tests.plugins.test_default_bucket'}
        return settings

    def test_an_event_is_sent_on_implicit_bucket_creation(self):
        bucket_url = '/buckets/default'
        self.app.get(bucket_url, headers=self.headers)
        assert len(_events) == 1
        assert 'last_modified' in _events[-1].impacted_records[0]['new']
        payload = _events[-1].payload
        assert payload['resource_name'] == 'bucket'
        assert payload['action'] == 'create'

    def test_an_event_is_sent_on_implicit_collection_creation(self):
        collection_url = '/buckets/default/collections/articles'
        self.app.get(collection_url, headers=self.headers)
        assert len(_events) == 2
        payload = _events[-1].payload
        assert payload['resource_name'] == 'collection'
        assert payload['action'] == 'create'

    def test_events_sent_on_bucket_and_collection_creation(self):
        records_uri = '/buckets/default/collections/articles/records/implicit'
        body = {"data": {"implicit": "creations"}}
        self.app.put_json(records_uri, body, headers=self.headers)

        assert len(_events) == 3

        # Implicit creation of bucket
        resp = self.app.get('/', headers=self.headers)
        bucket_id = resp.json['user']['bucket']
        assert 'subpath' not in _events[0].payload
        assert _events[0].payload['action'] == 'create'
        assert _events[0].payload['bucket_id'] == bucket_id
        assert _events[0].payload['uri'] == '/buckets/{}'.format(bucket_id)

        # Implicit creation of collection
        assert 'subpath' not in _events[1].payload
        assert _events[1].payload['action'] == 'create'
        assert _events[1].payload['resource_name'] == 'collection'
        assert _events[1].payload['bucket_id'] == bucket_id
        assert _events[1].payload['collection_id'] == 'articles'
        assert _events[1].payload['uri'] == '/buckets/{}/collections/articles'.format(bucket_id)

        # Creation of record
        assert _events[2].payload['action'] == 'create'
        assert _events[2].payload['resource_name'] == 'record'
        assert _events[2].payload['bucket_id'] == bucket_id
        assert _events[2].payload['collection_id'] == 'articles'
        assert _events[2].payload['uri'] == records_uri.replace('default',
                                                                bucket_id)

    def test_second_call_on_default_bucket_doesnt_send_create_events(self):
        bucket_url = '/buckets/default'
        self.app.get(bucket_url, headers=self.headers)
        # An event is generated -- it's the same event from
        # test_an_event_is_sent_on_implicit_bucket_creation.
        assert len(_events) == 1
        self.app.get(bucket_url, headers=self.headers)
        # Bucket shouldn't be created again, so there shouldn't be any
        # more events.
        assert len(_events) == 1

    def test_second_call_on_default_bucket_collection_doesnt_send_create_events(self):
        collection_url = '/buckets/default/collections/articles'
        self.app.get(collection_url, headers=self.headers)
        # Events are generated -- they're the same event from
        # test_an_event_is_sent_on_implicit_collection_creation.
        assert len(_events) == 2
        self.app.get(collection_url, headers=self.headers)
        # Neither the bucket nor the collection should be created
        # again, so there shouldn't be any more events.
        assert len(_events) == 2


class ReadonlyDefaultBucket(DefaultBucketWebTest):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['readonly'] = True
        return settings

    def test_implicit_creation_is_rejected(self):
        self.app.get('/buckets/default', headers=self.headers, status=405)


class BackendErrorTest(DefaultBucketWebTest):
    def setUp(self):
        super().setUp()
        self.patcher = mock.patch.object(
            self.storage, 'create',
            side_effect=storage_exceptions.BackendError())
        self.addCleanup(self.patcher.stop)

    def test_implicit_bucket_creation_raises_503_if_backend_fails(self):
        self.patcher.start()
        self.app.get('/buckets/default', headers=self.headers, status=503)

    def test_implicit_collection_creation_raises_503_if_backend_fails(self):
        self.app.get('/buckets/default', headers=self.headers)
        self.patcher.start()
        self.app.get('/buckets/default/collections/articles',
                     headers=self.headers, status=503)
