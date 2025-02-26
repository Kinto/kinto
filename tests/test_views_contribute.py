from kinto.core.testing import unittest

from .support import BaseWebTest


class ContributeViewTest(BaseWebTest, unittest.TestCase):
    def test_returns_info_about_project(self):
        response = self.app.get("/contribute.json")
        keys = sorted(response.json.keys())
        expected = ["bugs", "description", "keywords", "name", "participate", "repository"]
        self.assertEqual(keys, expected)
