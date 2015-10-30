import mock
from six import text_type
from uuid import UUID

from cliquet.errors import ERRORS
from cliquet.tests.support import FormattedErrorMixin
from cliquet.utils import hmac_digest

from .support import (BaseWebTest, unittest, get_user_headers,
                      MINIMALIST_RECORD)


class DefaultBucketViewTest(FormattedErrorMixin, BaseWebTest,
                            unittest.TestCase):

    bucket_url = '/buckets/default'
    collection_url = '/buckets/default/collections/tasks'

    def _follow(self, method, *args, **kwargs):
        status = kwargs.pop('status', None)
        response = method(*args, **kwargs)
        if response.status_code in (307, 308):
            location = response.headers['Location']
            location = location.replace('http://localhost/v1', '')
            kwargs['status'] = status
            response = method(location, *args[1:], **kwargs)
        return response

    def test_default_bucket_exists_and_has_user_id(self):
        bucket = self._follow(self.app.get, self.bucket_url,
                              headers=self.headers)
        result = bucket.json
        settings = self.app.app.registry.settings
        hmac_secret = settings['userid_hmac_secret']
        bucket_id = hmac_digest(hmac_secret, self.principal)[:32]

        self.assertEqual(result['data']['id'], text_type(UUID(bucket_id)))
        self.assertEqual(result['permissions']['write'], [self.principal])

    def test_default_bucket_can_still_be_explicitly_created(self):
        bucket = {'permissions': {'read': ['system.Everyone']}}
        resp = self._follow(self.app.put_json, self.bucket_url, bucket,
                            headers=self.headers)
        result = resp.json
        self.assertIn('system.Everyone', result['permissions']['read'])

    def test_default_bucket_collections_are_automatically_created(self):
        self._follow(self.app.get, self.collection_url, status=200,
                     headers=self.headers)

    def test_adding_a_task_for_bob_doesnt_add_it_for_alice(self):
        record = MINIMALIST_RECORD.copy()
        records_url = self.collection_url + '/records'
        resp = self._follow(self.app.post_json, records_url, record,
                            headers=get_user_headers('bob'))
        record_id = self.collection_url + '/records/' + resp.json['data']['id']
        resp = self._follow(self.app.get, record_id, status=404,
                            headers=get_user_headers('alice'))

    def test_unauthenticated_bucket_access_raises_json_401(self):
        resp = self.app.get(self.bucket_url, status=401)
        self.assertEquals(resp.json['message'],
                          'Please authenticate yourself to use this endpoint.')

    def test_bucket_id_is_an_uuid_with_dashes(self):
        bucket = self._follow(self.app.get, self.bucket_url,
                              headers=self.headers)
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
        full_url = self.collection_url + '/records?_since=invalid'
        self._follow(self.app.get, full_url, status=400,
                     headers=self.headers)

    def test_option_is_possible_without_authentication_for_default(self):
        headers = 'authorization,content-type'
        self.app.options(self.collection_url + '/records',
                         headers={
                             'Origin': 'http://localhost:8000',
                             'Access-Control-Request-Method': 'GET',
                             'Access-Control-Request-Headers': headers})

    def test_cors_headers_are_provided_on_errors(self):
        records_url = self.collection_url + '/records'
        resp = self._follow(self.app.post_json, records_url, MINIMALIST_RECORD,
                            headers=self.headers)
        current = resp.json['data']['last_modified']
        headers = self.headers.copy()
        headers.update({
            'Origin': 'http://localhost:8000',
            'If-None-Match': ('"%s"' % current).encode('utf-8')
        })
        resp = self._follow(self.app.get, self.collection_url + '/records',
                            headers=headers, status=304)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_cors_headers_are_provided_on_redirection(self):
        headers = self.headers.copy()
        headers['Origin'] = 'http://localhost:8000'
        resp = self.app.get(self.bucket_url, headers=headers, status=307)
        self.assertIn('Access-Control-Allow-Origin', resp.headers)

    def test_bucket_id_starting_with_default_can_still_be_created(self):
        # We need to create the bucket first since it is not the default bucket
        classic_bucket = self.bucket_url.replace('default', 'default-1234')
        resp = self._follow(self.app.put, classic_bucket, status=201,
                            headers=self.headers)
        bucket_id = resp.json['data']['id']
        self.assertEquals(bucket_id, 'default-1234')

        # We can then create the collection
        collection_url = '/buckets/default-1234/collections/default'
        self._follow(self.app.put, collection_url, status=201,
                     headers=self.headers)
        resp = self._follow(self.app.get, '/buckets/default-1234/collections',
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
        self._follow(self.app.put, self.collection_url, status=201,
                     headers=self.headers)

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

    def test_405_is_a_valid_formatted_error(self):
        response = self._follow(self.app.post, self.collection_url, status=405,
                                headers=self.headers)
        self.assertFormattedError(
            response, 405, ERRORS.METHOD_NOT_ALLOWED, "Method Not Allowed",
            "Method not allowed on this endpoint.")
