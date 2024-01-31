import os
import tempfile
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

    def test_admin_index_can_be_reached(self):
        self.maxDiff = None
        resp = self.app.get("/admin/")
        assert "<html>" in resp.body.decode("utf-8")

    def test_admin_redirect_without_trailing_slash(self):
        resp = self.app.get("/admin", status=307)
        self.assertTrue(resp.headers["location"].endswith("/admin/"))

    def test_admin_has_csp_header(self):
        resp = self.app.get("/admin/")
        assert "default-src 'self'" in resp.headers["Content-Security-Policy"]
        # The cached version too.
        resp = self.app.get("/admin/")
        assert "default-src 'self'" in resp.headers["Content-Security-Policy"]


class OverriddenAdminViewTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def make_app(cls, *args, **kwargs):
        cls.tmp_dir = tempfile.TemporaryDirectory()
        with open(os.path.join(cls.tmp_dir.name, "VERSION"), "w") as f:
            f.write("42.0.0")
        with open(os.path.join(cls.tmp_dir.name, "index.html"), "w") as f:
            f.write("mine!")
        with open(os.path.join(cls.tmp_dir.name, "script.js"), "w") as f:
            f.write("kiddy")
        return super().make_app(*args, **kwargs)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.tmp_dir.cleanup()

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = "kinto.plugins.admin"
        settings["admin_assets_path"] = cls.tmp_dir.name
        return settings

    def test_admin_capability_reads_version_from_configured_folder(self):
        resp = self.app.get("/")
        self.assertEqual(resp.json["capabilities"]["admin"]["version"], "42.0.0")

    def test_admin_ui_is_served_from_configured_folder(self):
        resp = self.app.get("/admin/")
        self.assertIn("mine!", resp.body.decode("utf-8"))

    def test_assets_are_served_from_configured_folder(self):
        resp = self.app.get("/admin/script.js")
        self.assertIn("kiddy", resp.body.decode("utf-8"))

    def test_original_assets_are_not_available(self):
        self.app.get("/admin/favicon.png", status=404)
