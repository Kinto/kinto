import mock

from .support import BaseWebTest, unittest, get_user_headers


class FlushViewTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(FlushViewTest, self).setUp()

        headers = self.headers.copy()
        headers.update(**get_user_headers('bob'))
        self.app.post('/collections/barley/records',
                      headers=headers, status=201)
        headers.update(**get_user_headers('alice'))
        self.app.post('/collections/chocolate/records',
                      headers=headers, status=201)

    def test_returns_405_if_not_enabled_in_configuration(self):
        self.app.post('/__flush__', headers=self.headers, status=405)

    def test_removes_every_records_in_every_collection_for_everyone(self):
        headers = self.headers.copy()
        with mock.patch.dict(self.app.app.registry.settings,
                             [('kinto.flush_endpoint_enabled', 'true')]):
            self.app.post('/__flush__', headers=self.headers, status=202)

        headers.update(**get_user_headers('bob'))
        results = self.app.get('/collections/barley/records',
                               headers=headers)
        self.assertEqual(results.json['items'], [])

        headers.update(**get_user_headers('alice'))
        results = self.app.get('/collections/chocolate/records',
                               headers=headers)
        self.assertEqual(results.json['items'], [])
