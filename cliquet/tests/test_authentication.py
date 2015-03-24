import base64
import hashlib
import time

import mock
from fxa import errors as fxa_errors

from cliquet import authentication
from cliquet.cache import redis as redis_backend

from .support import BaseWebTest, unittest, DummyRequest


class AuthenticationPoliciesTest(BaseWebTest, unittest.TestCase):

    sample_url = '/mushrooms'

    def test_basic_auth_is_accepted_if_enabled_in_settings(self):
        auth_password = base64.b64encode('bob:secret'.encode('ascii'))
        headers = {
            'Authorization': 'Basic {0}'.format(auth_password.decode('ascii'))
        }
        self.app.get(self.sample_url, headers=headers, status=401)

        with mock.patch.dict(self.app.app.registry.settings,
                             [('cliquet.basic_auth_enabled', 'true')]):
            self.app.get(self.sample_url, headers=headers, status=200)

    def test_views_are_forbidden_if_basic_is_wrong(self):
        headers = {
            'Authorization': 'Basic abc'
        }
        self.app.get(self.sample_url, headers=headers, status=401)

    def test_providing_empty_username_is_not_enough(self):
        auth_password = base64.b64encode(':secret'.encode('ascii'))
        headers = {
            'Authorization': 'Basic {0}'.format(auth_password.decode('ascii'))
        }
        self.app.get(self.sample_url, headers=headers, status=401)

    def test_views_are_forbidden_if_unknown_auth_method(self):
        self.headers['Authorization'] = 'Carrier'
        self.app.get(self.sample_url, headers=self.headers, status=401)
        self.headers['Authorization'] = 'Carrier pigeon'
        self.app.get(self.sample_url, headers=self.headers, status=401)

    def test_views_are_503_if_oauth2_server_misbehaves(self):
        self.fxa_verify.side_effect = fxa_errors.OutOfProtocolError
        self.app.get(self.sample_url, headers=self.headers, status=503)

    def test_views_are_forbidden_if_oauth2_error(self):
        self.fxa_verify.side_effect = fxa_errors.ClientError
        self.app.get(self.sample_url, headers=self.headers, status=401)

    def test_views_are_forbidden_if_oauth2_scope_mismatch(self):
        self.fxa_verify.side_effect = fxa_errors.TrustError
        self.app.get(self.sample_url, headers=self.headers, status=401)


class TokenVerificationCacheTest(unittest.TestCase):
    def setUp(self):
        cache = redis_backend.Redis(max_connections=1)
        self.cache = authentication.TokenVerificationCache(cache, 0.05)

    def test_set_adds_the_record(self):
        stored = 'toto'
        self.cache.set('foobar', stored)
        retrieved = self.cache.get('foobar')
        self.assertEquals(retrieved, stored)

    def test_delete_removes_the_record(self):
        self.cache.set('foobar', 'toto')
        self.cache.delete('foobar')
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)

    def test_set_expires_the_value(self):
        self.cache.set('foobar', 'toto')
        time.sleep(0.1)
        retrieved = self.cache.get('foobar')
        self.assertIsNone(retrieved)


class BasicAuthenticationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = authentication.BasicAuthAuthenticationPolicy()
        self.request = DummyRequest()
        self.request.headers['Authorization'] = 'Basic bWF0Og=='
        self.request.registry.settings['cliquet.basic_auth_enabled'] = True

    def test_prefixes_users_with_basicauth(self):
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertTrue(user_id.startswith('basicauth_'))

    @mock.patch('cliquet.authentication.hmac.new')
    def test_userid_is_hashed(self, mocked):
        mocked.return_value = hashlib.sha224('hashed'.encode('utf8'))
        user_id = self.policy.unauthenticated_userid(self.request)
        self.assertIn('fc04599e80aed4e56d3465', user_id)

    def test_userid_is_built_using_password(self):
        self.request.headers['Authorization'] = 'Basic bWF0OjE='
        user_id1 = self.policy.unauthenticated_userid(self.request)
        self.request.headers['Authorization'] = 'Basic bWF0OjI='
        user_id2 = self.policy.unauthenticated_userid(self.request)
        self.assertNotEqual(user_id1, user_id2)
