import mock
import requests

from .support import BaseWebTest, unittest


httpOK = requests.models.Response()
httpOK.status_code = 200


class SuccessTest(BaseWebTest, unittest.TestCase):

    @mock.patch('requests.get')
    def test_returns_storage_true_if_ok(self, get_mocked):
        get_mocked.return_value = httpOK
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['storage'], True)

    @mock.patch('requests.get')
    def test_returns_cache_true_if_ok(self, get_mocked):
        get_mocked.return_value = httpOK
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['cache'], True)

    def test_successful_if_one_heartbeat_is_none(self):
        self.app.app.registry.heartbeats['probe'] = lambda r: None
        response = self.app.get('/__heartbeat__', status=200)
        self.assertEqual(response.json['probe'], None)


class FailureTest(BaseWebTest, unittest.TestCase):

    @mock.patch('requests.get')
    def test_returns_storage_false_if_ko(self, get_mocked):
        self.app.app.registry.heartbeats['storage'] = lambda r: False
        get_mocked.return_value = httpOK
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['storage'], False)

    @mock.patch('requests.get')
    def test_returns_cache_false_if_ko(self, get_mocked):
        self.app.app.registry.heartbeats['cache'] = lambda r: False
        get_mocked.return_value = httpOK
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['cache'], False)


class LoadBalancerHeartbeat(BaseWebTest, unittest.TestCase):
    def test_returns_200_with_empty_body(self):
        resp = self.app.get('/__lbheartbeat__', status=200)
        self.assertEqual(resp.json, {})
