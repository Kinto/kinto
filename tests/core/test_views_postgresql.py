import unittest

from kinto.core.testing import skip_if_no_postgresql

from .support import PostgreSQLTest


@skip_if_no_postgresql
class PaginationTest(PostgreSQLTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["storage_max_fetch_size"] = 4
        return settings

    def setUp(self):
        super().setUp()
        for i in range(10):
            self.app.post_json('/mushrooms', {'data': {'name': str(i)}},
                               headers=self.headers)

    def test_storage_max_fetch_size_is_per_page(self):
        resp = self.app.get('/mushrooms?_limit=6', headers=self.headers)
        self.assertIn("Next-Page", resp.headers)
        self.assertEqual(int(resp.headers["Total-Records"]), 10)
        self.assertEqual(len(resp.json['data']), 4)

        next_page_url = resp.headers["Next-Page"].replace("http://localhost/v0", "")
        resp = self.app.get(next_page_url, headers=self.headers)
        self.assertIn("Next-Page", resp.headers)
        self.assertEqual(int(resp.headers["Total-Records"]), 10)
        self.assertEqual(len(resp.json['data']), 4)

        next_page_url = resp.headers["Next-Page"].replace("http://localhost/v0", "")
        resp = self.app.get(next_page_url, headers=self.headers)
        self.assertNotIn("Next-Page", resp.headers)
        self.assertEqual(int(resp.headers["Total-Records"]), 10)
        self.assertEqual(len(resp.json['data']), 2)
