import mock

from kinto.core.testing import unittest

from .support import BaseWebTest


class SuccessTest(BaseWebTest, unittest.TestCase):

    def test_returns_storage_true_if_ok(self):
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['storage'], True)

    def test_returns_cache_true_if_ok(self):
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['cache'], True)

    def test_successful_if_one_heartbeat_is_none(self):
        self.app.app.registry.heartbeats['probe'] = lambda r: None
        response = self.app.get('/__heartbeat__', status=200)
        self.assertEqual(response.json['probe'], None)


class FailureTest(BaseWebTest, unittest.TestCase):

    def setUp(self):
        self._heartbeats = {**self.app.app.registry.heartbeats}
        super().setUp()

    def tearDown(self):
        self.app.app.registry.heartbeats = self._heartbeats
        super().tearDown()

    def test_returns_storage_false_if_ko(self):
        self.app.app.registry.heartbeats['storage'] = lambda r: False
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['storage'], False)
        self.assertEqual(response.json['cache'], True)

    def test_returns_cache_false_if_ko(self):
        self.app.app.registry.heartbeats['cache'] = lambda r: False
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['cache'], False)
        self.assertEqual(response.json['storage'], True)

    def test_returns_false_if_heartbeat_times_out(self):
        def sleepy(request):
            import time
            time.sleep(1)
        self.app.app.registry.heartbeats['cache'] = sleepy
        with mock.patch.dict(self.app.app.registry.settings,
                             [('heartbeat_timeout_seconds', 0.1)]):
            response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['cache'], False)
        self.assertEqual(response.json['storage'], True)

    def test_returns_false_if_heartbeat_fails(self):
        self.app.app.registry.heartbeats['cache'] = lambda r: 1 / 0
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['cache'], False)
        self.assertEqual(response.json['storage'], True)


class LoadBalancerHeartbeat(BaseWebTest, unittest.TestCase):
    def test_returns_200_with_empty_body(self):
        resp = self.app.get('/__lbheartbeat__', status=200)
        self.assertEqual(resp.json, {})
