import base64

import mock
from fxa import errors as fxa_errors

from .support import BaseWebTest, unittest


class AuthenticationPoliciesTest(BaseWebTest, unittest.TestCase):

    sample_url = '/articles'

    def test_basic_auth_is_accepted_if_enabled_in_settings(self):
        auth_password = base64.b64encode('bob:secret'.encode('ascii'))
        headers = {
            'Authorization': 'Basic {0}'.format(auth_password.decode('ascii'))
        }
        self.app.get(self.sample_url, headers=headers, status=401)

        with mock.patch.dict(self.app.app.registry.settings,
                             [('readinglist.basic_auth_backdoor', 'true')]):
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
