from .support import BaseWebTest, unittest


class BatchViewTest(BaseWebTest, unittest.TestCase):

    def test_returns_empty_response_if_empty_requests(self):
        resp = self.app.post('/batch', {}, headers=self.headers)
        self.assertEqual(resp.json, {})
