import base64
import unittest

import mock

from .support import BaseWebTest

from fxa import errors as fxa_errors


class AuthenticationPoliciesTest(BaseWebTest, unittest.TestCase):

    sample_url = '/articles'

    @mock.patch('readinglist.authentication.check_credentials')
    def test_basic_auth_is_accepted(self, check_mocked):
        auth_password = base64.b64encode('bob:secret')
        headers = {
            'Authorization': 'Basic {}'.format(auth_password)
        }
        self.app.get('/articles', headers=headers)
        check_mocked.assertIsCalled()

    def test_views_are_forbidden_if_basic_is_wrong(self):
        headers = {
            'Authorization': 'Basic abc'
        }
        self.app.get(self.sample_url, headers=headers, status=403)

    def test_views_are_forbidden_if_unknown_auth_method(self):
        self.headers['Authorization'] = 'Carrier'
        self.app.get(self.sample_url, headers=self.headers, status=403)
        self.headers['Authorization'] = 'Carrier pigeon'
        self.app.get(self.sample_url, headers=self.headers, status=403)

    def test_views_are_503_if_oauth2_server_misbehaves(self):
        self.fxa_verify.side_effect = fxa_errors.OutOfProtocolError
        self.app.get(self.sample_url, headers=self.headers, status=503)

    def test_views_are_forbidden_if_oauth2_error(self):
        self.fxa_verify.side_effect = fxa_errors.ClientError
        self.app.get(self.sample_url, headers=self.headers, status=403)

    def test_views_are_forbidden_if_oauth2_scope_mismatch(self):
        self.fxa_verify.side_effect = fxa_errors.TrustError
        self.app.get(self.sample_url, headers=self.headers, status=403)
