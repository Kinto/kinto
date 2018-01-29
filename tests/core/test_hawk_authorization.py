import mock
import uuid

from pyramid.config import Configurator
from pyramid.exceptions import ConfigurationError

from kinto.core import DEFAULT_SETTINGS
from kinto.core.hawkauth import HawkAuth
from kinto.core import authentication
from kinto.core import utils
from kinto.core.testing import DummyRequest, unittest

from .support import BaseWebTest

# settings names
SETTING_NAME_MOHAWK_POWER_SWITCH = 'kinto.hawk.enabled'
SETTING_NAME_MOHAWK_CLIENT = 'kinto.hawk.id'
SETTING_NAME_MOHAWK_SECRET = 'kinto.hawk.secret'
SETTING_NAME_MOHAWK_ALGORITHM = 'kinto.hawk.algo'

# test credentials
TEST_CLIENT_ID = 'test_client'
TEST_SECRET = '8a6ebaf9-94fe-4c43-9d58-fb0aed2b24c7'
TEST_ALGORITHM = 'sha256'


hawk_settings = {
    SETTING_NAME_MOHAWK_POWER_SWITCH: False,
    SETTING_NAME_MOHAWK_CLIENT: TEST_CLIENT_ID,
    SETTING_NAME_MOHAWK_SECRET: TEST_SECRET,
    SETTING_NAME_MOHAWK_ALGORITHM: TEST_ALGORITHM
}

# Test configuration settings without sending credentials in request
class HawkRequestAuthorizationSettingsTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        self.policy = authentication.BasicAuthAuthenticationPolicy()
        self.request = DummyRequest()
        self.request.headers['Authorization'] = 'Basic bWF0Og=='

    def test_hawk_auth_is_ignored_if_disabled_in_settings(self):
        app = self.make_app(hawk_settings)
        app.get(self.collection_url, headers=self.headers, status=200)

    def test_hawk_auth_request_is_forbidden_if_settings_are_valid(self):
        # settings are valid but the request fails to send the correct signature
        enabled_hawk_settings = hawk_settings.copy()
        enabled_hawk_settings.update({
            SETTING_NAME_MOHAWK_POWER_SWITCH: True})
        app = self.make_app(enabled_hawk_settings)
        app.get(self.collection_url, headers=self.headers, status=401)
    
    def test_hawk_auth_raises_if_empty_client_id_or_secret_in_settings(self):
        settings = {**DEFAULT_SETTINGS}
        config = Configurator(settings=settings)
        config.registry.cache = {}

        invalid_hawk_settings = hawk_settings.copy()
        invalid_hawk_settings.update({
            SETTING_NAME_MOHAWK_POWER_SWITCH: True,
            SETTING_NAME_MOHAWK_CLIENT: ''})

        # empty client ID raises ConfigurationError
        with self.assertRaises(ConfigurationError):
            authenticator = HawkAuth(
                invalid_hawk_settings[SETTING_NAME_MOHAWK_CLIENT],
                invalid_hawk_settings[SETTING_NAME_MOHAWK_SECRET],
                invalid_hawk_settings[SETTING_NAME_MOHAWK_ALGORITHM],
                config)
        # empty secret raises ConfigurationError
        with self.assertRaises(ConfigurationError):
            authenticator = HawkAuth(
                TEST_CLIENT_ID,
                '',
                invalid_hawk_settings[SETTING_NAME_MOHAWK_ALGORITHM],
                config)

    def test_hawk_auth_raises_if_invalid_algorithm_in_settings(self):
        pass
        
# Mock request with HAWK credentials and test authentication
class HawkRequestAuthorizationTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        pass

    def test_hawk_auth_fails_if_secret_is_incorrect(self):
        pass

    def test_hawk_auth_fails_if_nonce_has_already_been_used(self):
        pass

    def test_hawk_auth_fails_when_timestamps_mismatch(self):
        pass

    def test_hawk_auth_succeeds_with_good_credentials(self):
        pass

