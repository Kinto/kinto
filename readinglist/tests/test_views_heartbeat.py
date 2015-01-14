import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from .support import BaseWebTest


class HeartBeatViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_database_true_if_ok(self):
        response = self.app.get('/__heartbeat__')
        self.assertEqual(response.json['database'], True)

    @mock.patch('readinglist.backend.memory.Memory.ping')
    def test_returns_database_false_if_ko(self, ping_mocked):
        ping_mocked.side_effect = IndexError
        response = self.app.get('/__heartbeat__', status=503)
        self.assertEqual(response.json['database'], False)
