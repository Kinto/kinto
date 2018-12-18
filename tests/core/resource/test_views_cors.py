from unittest import mock

from pyramid import httpexceptions

from kinto.core.testing import unittest

from ..support import BaseWebTest


MINIMALIST_OBJECT = {"name": "Champignon"}


class CORSOriginHeadersTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.headers["Origin"] = "notmyidea.org"

    def setUp(self):
        super().setUp()
        body = {"data": MINIMALIST_OBJECT}
        response = self.app.post_json(self.plural_url, body, headers=self.headers, status=201)
        self.obj = response.json["data"]

    def test_can_be_configured_from_settings(self):
        app = self.make_app({"cors_origins": "*.daybed.io"})
        headers = {**self.headers, "Origin": "demo.daybed.io"}
        resp = app.get(self.plural_url, headers=headers)
        self.assertEqual(resp.headers["Access-Control-Allow-Origin"], "demo.daybed.io")

    def test_present_on_hello(self):
        response = self.app.get("/", headers=self.headers, status=200)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_single_object(self):
        response = self.app.get(self.get_item_url(), headers=self.headers)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_deletion(self):
        response = self.app.delete(self.get_item_url(), headers=self.headers)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_unknown_url(self):
        response = self.app.get("/unknown", headers=self.headers, status=404)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "notmyidea.org")

    def test_not_present_on_unknown_url_if_setting_does_not_match(self):
        with mock.patch.dict(self.app.app.registry.settings, [("cors_origins", "daybed.io")]):
            response = self.app.get("/unknown", headers=self.headers, status=404)
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_unknown_object(self):
        url = self.get_item_url("1cea99eb-5e3d-44ad-a53a-2fb68473b538")
        response = self.app.get(url, headers=self.headers, status=404)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_invalid_object_update(self):
        body = {"data": {"name": 42}}
        response = self.app.patch_json(self.get_item_url(), body, headers=self.headers, status=400)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_successful_creation(self):
        body = {"data": MINIMALIST_OBJECT}
        response = self.app.post_json(self.plural_url, body, headers=self.headers, status=201)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_invalid_object_creation(self):
        body = {"name": 42}
        response = self.app.post_json(self.plural_url, body, headers=self.headers, status=400)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_readonly_update(self):
        with mock.patch("tests.core.testapp.views.MushroomSchema.is_readonly", return_value=True):
            body = {"data": {"name": "Amanite"}}
            response = self.app.patch_json(
                self.get_item_url(), body, headers=self.headers, status=400
            )
        self.assertEqual(response.json["message"], "Cannot modify name")
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_unauthorized(self):
        headers = {**self.headers}
        headers.pop("Authorization", None)
        body = {"data": MINIMALIST_OBJECT}
        response = self.app.post_json(self.plural_url, body, headers=headers, status=401)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_internal_error(self):
        with mock.patch("kinto.core.resource.Resource._extract_filters", side_effect=ValueError):
            response = self.app.get("/mushrooms", headers=self.headers, status=500)
        self.assertIn("Access-Control-Allow-Origin", response.headers)

    def test_present_on_http_error(self):
        with mock.patch(
            "kinto.core.resource.Resource._extract_filters",
            side_effect=httpexceptions.HTTPPaymentRequired,
        ):
            response = self.app.get("/mushrooms", headers=self.headers, status=402)
        self.assertIn("Access-Control-Allow-Origin", response.headers)


class CORSExposeHeadersTest(BaseWebTest, unittest.TestCase):
    def assert_expose_headers(self, method, path, allowed_headers, body=None, status=None):
        headers = {**self.headers, "Origin": "lolnet.org"}
        http_method = getattr(self.app, method.lower())
        kwargs = dict(headers=headers)
        if status:
            kwargs["status"] = status
        if method == "HEAD":
            # TestApp.head can't take a 'params' and its first and only positional argument.
            # So we need an ad-hoc signature for TestApp.head.
            response = http_method(path, **kwargs)
        else:
            response = http_method(path, body, **kwargs)
        exposed_headers = response.headers["Access-Control-Expose-Headers"]
        exposed_headers = [x.strip() for x in exposed_headers.split(",")]
        self.assertEqual(sorted(allowed_headers), sorted(exposed_headers))
        return response

    def test_plural_get_exposes_every_possible_header(self):
        self.assert_expose_headers(
            "GET",
            self.plural_url,
            [
                "Alert",
                "Backoff",
                "ETag",
                "Last-Modified",
                "Next-Page",
                "Retry-After",
                "Content-Length",
                "Cache-Control",
                "Expires",
                "Pragma",
            ],
        )

    def test_plural_head_exposes_every_possible_header(self):
        self.assert_expose_headers(
            "HEAD",
            self.plural_url,
            [
                "Alert",
                "Backoff",
                "ETag",
                "Last-Modified",
                "Retry-After",
                "Total-Objects",
                "Total-Records",
                "Content-Length",
                "Cache-Control",
                "Expires",
                "Next-Page",
                "Pragma",
            ],
        )

    def test_hello_endpoint_exposes_only_minimal_set_of_headers(self):
        self.assert_expose_headers(
            "GET", "/", ["Alert", "Backoff", "Retry-After", "Content-Length"]
        )

    def test_object_get_exposes_only_used_headers(self):
        body = {"data": MINIMALIST_OBJECT}
        resp = self.app.post_json(self.plural_url, body, headers=self.headers, status=201)
        object_url = self.get_item_url(resp.json["data"]["id"])
        self.assert_expose_headers(
            "GET",
            object_url,
            [
                "Alert",
                "Backoff",
                "ETag",
                "Retry-After",
                "Last-Modified",
                "Content-Length",
                "Cache-Control",
                "Expires",
                "Pragma",
            ],
        )

    def test_object_post_exposes_only_minimal_set_of_headers(self):
        body = {"data": MINIMALIST_OBJECT}
        self.assert_expose_headers(
            "POST_JSON",
            "/mushrooms",
            ["Alert", "Backoff", "Retry-After", "Content-Length"],
            body=body,
        )

    def test_present_on_bad_id_400_errors(self):
        body = {"data": {"name": "Amanite"}}
        self.assert_expose_headers(
            "PUT_JSON",
            "/mushrooms/wrong=ids",
            ["Alert", "Backoff", "Retry-After", "Content-Length"],
            body=body,
            status=400,
        )

    def test_present_on_unknown_url(self):
        self.assert_expose_headers(
            "PUT_JSON",
            "/unknown",
            ["Alert", "Backoff", "Retry-After", "Content-Length"],
            status=404,
        )


class CORSMaxAgeTest(BaseWebTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.headers.update({"Origin": "lolnet.org", "Access-Control-Request-Method": "GET"})

    def test_cors_max_age_is_3600_seconds_by_default(self):
        app = self.make_app()
        resp = app.options("/", headers=self.headers)
        self.assertEqual(int(resp.headers["Access-Control-Max-Age"]), 3600)

    def test_cors_max_age_can_be_specified_in_settings(self):
        app = self.make_app({"cors_max_age_seconds": "42"})
        resp = app.options("/", headers=self.headers)
        self.assertEqual(int(resp.headers["Access-Control-Max-Age"]), 42)

    def test_cors_max_age_is_disabled_if_unset(self):
        app = self.make_app({"cors_max_age_seconds": ""})
        resp = app.options("/", headers=self.headers)
        self.assertNotIn("Access-Control-Max-Age", resp.headers)
