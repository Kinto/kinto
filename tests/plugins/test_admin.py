import os
import unittest

from kinto.plugins.admin import views as admin_views
from ..support import BaseWebTest


admin_module = os.path.dirname(admin_views.__file__)
build_folder = os.path.join(admin_module, "build")
built_index = os.path.join(build_folder, "index.html")


class AdminViewTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Simulate admin bundle without npm
        os.makedirs(build_folder, exist_ok=True)
        with open(built_index, "w") as f:
            f.write("<html><script/></html>")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        try:
            os.remove(built_index)
        except FileNotFoundError:
            pass

    @classmethod
    def get_app_settings(self, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.admin"
        return settings

    def setUp(self):
        admin_views.admin_home_view.saved = None

    def test_capability_is_exposed(self):
        self.maxDiff = None
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("admin", capabilities)
        self.assertIn("version", capabilities["admin"])
        del capabilities["admin"]["version"]
        expected = {
            "description": "Serves the admin console.",
            "url": ("https://github.com/Kinto/kinto-admin/"),
        }
        self.assertEqual(expected, capabilities["admin"])

    def test_permission_endpoint_is_enabled_with_admin(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        assert "permissions_endpoint" in capabilities

    def test_admin_index_cat_be_reached(self):
        self.maxDiff = None
        resp = self.app.get("/admin/")
        assert "html" in resp.body.decode("utf-8")

    def test_admin_redirect_without_trailing_slash(self):
        resp = self.app.get("/admin", status=307)
        self.assertTrue(resp.headers["location"].endswith("/admin/"))
