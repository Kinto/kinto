import mock

from .support import BaseWebTest, unittest


class HeartBeatViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_database_true_if_ok(self):
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['database'], True)

    @mock.patch('cliquet.storage.memory.Memory.ping')
    @mock.patch('cliquet.storage.redis.Redis.ping')
    def test_returns_database_false_if_ko(self, *mocked):
        for mock_instance in mocked:
            mock_instance.return_value = False
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['database'], False)
