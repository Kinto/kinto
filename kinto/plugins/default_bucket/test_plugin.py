import mock
from six import text_type
from uuid import UUID

from pyramid.httpexceptions import HTTPBadRequest

from cliquet.errors import ERRORS, http_error
from cliquet.storage import exceptions as storage_exceptions
from cliquet.tests.support import FormattedErrorMixin
from cliquet.utils import hmac_digest

from kinto.tests.support import (BaseWebTest, unittest, get_user_headers,
                                 MINIMALIST_RECORD)


class DefaultBucketViewTest(FormattedErrorMixin, BaseWebTest,
                            unittest.TestCase):

    bucket_url = '/buckets/default'
    collection_url = '/buckets/default/collections/tasks'

    def test_default_bucket_exists_and_has_user_id(self):
        bucket = self.app.get(self.bucket_url, headers=self.headers)
        result = bucket.json
        settings = self.app.app.registry.settings
        hmac_secret = settings['userid_hmac_secret']
        bucket_id = hmac_digest(hmac_secret, self.principal)[:32]

        self.assertEqual(result['data']['id'], text_type(UUID(bucket_id)))
        self.assertEqual(result['permissions']['write'], [self.principal])

    def test_default_bucket_can_still_be_explicitly_created(self):
        bucket = {'permissions': {'read': ['system.Everyone']}}
        resp = self.app.put_json(self.bucket_url, bucket, headers=self.headers)
        result = resp.json
        self.assertIn('system.Everyone', result['permissions']['read'])

    def test_default_bucket_collections_are_automatically_created(self):
        self.app.get(self.collection_url, headers=self.headers, status=200)

    def test_adding_a_task_for_bob_doesnt_add_it_for_alice(self):
        record = MINIMALIST_RECORD.copy()
        resp = self.app.post_json(self.collection_url + '/records',
                                  record, headers=get_user_headers('bob'))
        record_id = self.collection_url + '/records/' + resp.json['data']['id']
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
            self.fail('bucket_id: %s is not a valid UUID.' % bucket_id)

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
        headers = self.headers.copy()
        headers.update({
            'Origin': 'http://localhost:8000',
            'If-None-Match': ('"%s"' % current).encode('utf-8')
        })
        resp = self.app.get(self.collection_url + '/records',
                            headers=headers, status=304)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)
        self.assertIn('ETag', resp.headers['Access-Control-Expose-Headers'])

    def test_etag_is_present_and_exposed_in_304_error(self):
        resp = self.app.post_json(self.collection_url + '/records',
                                  MINIMALIST_RECORD,
                                  headers=self.headers)
        current = resp.json['data']['last_modified']
        headers = self.headers.copy()
        headers.update({
            'Origin': 'http://localhost:8000',
            'If-None-Match': ('"%s"' % current).encode('utf-8')
        })
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

        with mock.patch.object(self.storage, 'get',
                               wraps=self.storage.get) as patched:
            self.app.post_json('/batch', batch, headers=self.headers)
            self.assertEqual(patched.call_count, 0)

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

        with mock.patch.object(self.storage, 'get',
                               wraps=self.storage.get) as patched:
            self.app.post_json('/batch', batch, headers=self.headers)
            self.assertEqual(patched.call_count, 0)

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


class HelloViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_bucket_id_and_url_if_authenticated(self):
        response = self.app.get('/', headers=self.headers)
        self.assertEqual(response.json['user']['bucket'],
                         '23bb0efc-e80d-829e-6757-79d41e16640f')

    def test_flush_capability_if_enabled(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('default_bucket', capabilities)


_events = []


def load_from_config(config, prefix):
    def listener(event):
        _events.append(event)

    return listener


class EventsTest(BaseWebTest, unittest.TestCase):
    def tearDown(self):
        super(EventsTest, self).tearDown()
        del _events[:]

    def get_app_settings(self, extra=None):
        settings = super(EventsTest, self).get_app_settings(extra)
        settings['event_listeners'] = 'testevent',
        settings['event_listeners.testevent.use'] = (
            'kinto.plugins.default_bucket.test_plugin')
        return settings

    def test_an_event_is_sent_on_implicit_bucket_creation(self):
        bucket_url = '/buckets/default'
        self.app.get(bucket_url, headers=self.headers)
        assert len(_events) == 1
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
        records_uri = '/buckets/default/collections/articles/records'
        self.app.get(records_uri, headers=self.headers)

        assert len(_events) == 2

        # XXX: Could not achieve a behaviour the payload uri reflect the
        # underlying created object.
        # resp = self.app.get('/', headers=self.headers)
        # bucket_id = resp.json['user']['bucket']
        # assert _events[0].payload['uri'] == '/buckets/%s' % bucket_id
        # assert _events[1].payload['uri'] == (
        #     '/buckets/%s/collections/articles' % bucket_id)


class ReadonlyDefaultBucket(BaseWebTest, unittest.TestCase):

    def get_app_settings(self, extras=None):
        settings = super(ReadonlyDefaultBucket, self).get_app_settings(extras)
        settings['readonly'] = True
        return settings

    def test_implicit_creation_is_rejected(self):
        self.app.get('/buckets/default', headers=self.headers, status=405)


class BackendErrorTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(BackendErrorTest, self).setUp()
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
