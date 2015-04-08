import mock
import requests

from .support import BaseWebTest, unittest


class SuccessTest(BaseWebTest, unittest.TestCase):

    @mock.patch('cliquet.views.heartbeat.fxa_ping')
    def test_returns_storage_true_if_ok(self, *mocked):
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['database'], True)

    @mock.patch('cliquet.views.heartbeat.fxa_ping')
    def test_returns_cache_true_if_ok(self, *mocked):
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['cache'], True)

    @mock.patch('requests.get')
    def test_returns_oauth_true_if_ok(self, get_mocked):
        response = requests.models.Response()
        response.status_code = 200
        get_mocked.return_value = response
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['oauth'], True)

    def test_returns_oauth_none_if_oauth_deactivated(self):
        with mock.patch.dict(self.app.app.registry.settings,
                             [('fxa-oauth.oauth_uri', None)]):
            response = self.app.get('/__heartbeat__', status=200)
            self.assertEqual(response.json['oauth'], None)


class FailureTest(BaseWebTest, unittest.TestCase):

    @mock.patch('cliquet.views.heartbeat.fxa_ping')
    @mock.patch('cliquet.storage.redis.Redis.ping')
    @mock.patch('cliquet.storage.memory.Memory.ping')
    def test_returns_storage_false_if_ko(self, *mocked):
        for mock_instance in mocked:
            mock_instance.return_value = False
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['database'], False)

    @mock.patch('cliquet.views.heartbeat.fxa_ping')
    @mock.patch('cliquet.cache.redis.Redis.ping')
    def test_returns_cache_false_if_ko(self, *mocked):
        for mock_instance in mocked:
            mock_instance.return_value = False
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['cache'], False)

    @mock.patch('requests.get')
    def test_returns_oauth_false_if_ko(self, *mocked):
        for mock_instance in mocked:
            mock_instance.side_effect = requests.exceptions.HTTPError()
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['oauth'], False)
