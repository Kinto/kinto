import unittest
from unittest import mock

from pyramid import httpexceptions

from kinto.core.errors import ERRORS, http_error
from kinto.core.testing import FormattedErrorMixin
from kinto.core.storage import exceptions as storage_exceptions

from .support import BaseWebTest


class ErrorViewTest(FormattedErrorMixin, BaseWebTest, unittest.TestCase):

    sample_url = "/mushrooms"

    def test_backoff_headers_is_not_present_by_default(self):
        response = self.app.get(self.sample_url, headers=self.headers, status=200)
        self.assertNotIn("Backoff", response.headers)

    def test_backoff_headers_is_present_if_configured(self):
        with mock.patch.dict(self.app.app.registry.settings, [("backoff", 10)]):
            response = self.app.get(self.sample_url, headers=self.headers, status=200)
        self.assertIn("Backoff", response.headers)
        self.assertEqual(response.headers["Backoff"], "10")

    def test_backoff_headers_is_present_if_less_than_percentage(self):
        with mock.patch.dict(
            self.app.app.registry.settings, [("backoff", 10), ("backoff_percentage", 50)]
        ):
            with mock.patch("kinto.core.initialization.random.random", return_value=0.4):
                response = self.app.get(self.sample_url, headers=self.headers, status=200)
        self.assertIn("Backoff", response.headers)
        self.assertEqual(response.headers["Backoff"], "10")

    def test_backoff_headers_is_not_present_if_greater_than_percentage(self):
        with mock.patch.dict(
            self.app.app.registry.settings, [("backoff", 10), ("backoff_percentage", 50)]
        ):
            with mock.patch("kinto.core.initialization.random.random", return_value=0.6):
                response = self.app.get(self.sample_url, headers=self.headers, status=200)
        self.assertNotIn("Backoff", response.headers)

    def test_backoff_headers_is_present_on_304(self):
        first = self.app.get(self.sample_url, headers=self.headers)
        etag = first.headers["ETag"]
        headers = {**self.headers, "If-None-Match": etag}
        with mock.patch.dict(self.app.app.registry.settings, [("backoff", 10)]):
            response = self.app.get(self.sample_url, headers=headers, status=304)
        self.assertIn("Backoff", response.headers)

    def test_backoff_header_is_present_on_error_responses(self):
        with mock.patch.dict(self.app.app.registry.settings, [("backoff", 10)]):
            with mock.patch(
                "tests.core.testapp.views.Mushroom._extract_filters", side_effect=ValueError
            ):
                response = self.app.get(self.sample_url, headers=self.headers, status=500)
        self.assertIn("Backoff", response.headers)

    def test_404_is_valid_formatted_error(self):
        response = self.app.get("/unknown", status=404)
        self.assertFormattedError(
            response,
            404,
            ERRORS.MISSING_RESOURCE,
            "Not Found",
            "The resource you are looking for could not be found.",
        )

    def test_404_can_be_overridden(self):
        custom_404 = http_error(
            httpexceptions.HTTPNotFound(), errno=ERRORS.MISSING_RESOURCE, message="Customized."
        )
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=custom_404
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=404)
        self.assertFormattedError(
            response, 404, ERRORS.MISSING_RESOURCE, "Not Found", "Customized."
        )

    def test_401_is_valid_formatted_error(self):
        response = self.app.get(self.sample_url, status=401)  # no headers
        self.assertFormattedError(
            response,
            401,
            ERRORS.MISSING_AUTH_TOKEN,
            "Unauthorized",
            "Please authenticate yourself to use this endpoint.",
        )

    def test_403_is_valid_formatted_error(self):
        with mock.patch("tests.core.support.AllowAuthorizationPolicy.permits", return_value=False):
            response = self.app.get(self.sample_url, headers=self.headers, status=403)
        self.assertFormattedError(
            response, 403, ERRORS.FORBIDDEN, "Forbidden", "This user cannot access this resource."
        )

    def test_403_can_be_overridded(self):
        custom_403 = http_error(
            httpexceptions.HTTPForbidden(), errno=ERRORS.FORBIDDEN, message="Customized."
        )
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=custom_403
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=403)
        self.assertFormattedError(response, 403, ERRORS.FORBIDDEN, "Forbidden", "Customized.")

    def test_405_is_valid_formatted_error(self):
        response = self.app.patch(self.sample_url, headers=self.headers, status=405)
        self.assertFormattedError(
            response,
            405,
            ERRORS.METHOD_NOT_ALLOWED,
            "Method Not Allowed",
            "Method not allowed on this endpoint.",
        )

    def test_405_can_have_custom_message(self):
        custom_405 = http_error(
            httpexceptions.HTTPMethodNotAllowed(),
            errno=ERRORS.METHOD_NOT_ALLOWED,
            message="Disabled from conf.",
        )
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=custom_405
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=405)
        self.assertFormattedError(
            response, 405, ERRORS.METHOD_NOT_ALLOWED, "Method Not Allowed", "Disabled from conf."
        )

    def test_500_is_valid_formatted_error(self):
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=ValueError
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=500)
        self.assertFormattedError(
            response,
            500,
            ERRORS.UNDEFINED,
            "Internal Server Error",
            "A programmatic error occured, developers have been informed.",
            "https://github.com/Kinto/kinto/issues/",
        )

    def test_400_with_invalid_url_path(self):
        response = self.app.get("/%82%AC", status=400)
        self.assertFormattedError(
            response, 400, ERRORS.INVALID_PARAMETERS, "Bad Request", "Invalid URL path."
        )

    def test_400_when_query_field_contains_nul_character(self):
        response = self.app.get(
            self.sample_url + '?field\x00="2"', headers=self.headers, status=400
        )
        self.assertFormattedError(
            response,
            400,
            ERRORS.INVALID_PARAMETERS,
            "Invalid parameters",
            "Invalid character 0x00",
        )

    def test_400_when_query_value_contains_nul_character(self):
        response = self.app.get(
            self.sample_url + '?field="\x00"', headers=self.headers, status=400
        )
        self.assertFormattedError(
            response,
            400,
            ERRORS.INVALID_PARAMETERS,
            "Invalid parameters",
            "Invalid character 0x00",
        )

    def test_info_link_in_error_responses_can_be_configured(self):
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=ValueError
        ):
            link = "https://github.com/mozilla-services/kinto/issues/"
            app = self.make_app({"error_info_link": link, "readonly": False})
            response = app.get(self.sample_url, headers=self.headers, status=500)
        self.assertFormattedError(
            response,
            500,
            ERRORS.UNDEFINED,
            "Internal Server Error",
            "A programmatic error occured, developers have been informed.",
            link,
        )

    def test_503_is_valid_formatted_error(self):
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters",
            side_effect=httpexceptions.HTTPServiceUnavailable,
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=503)
        self.assertFormattedError(
            response,
            503,
            ERRORS.BACKEND,
            "Service Unavailable",
            (
                "Service temporary unavailable "
                "due to overloading or maintenance, please retry later."
            ),
        )
        self.assertIn("Retry-After", response.headers)

    def test_503_can_have_custom_message(self):
        custom_503 = http_error(
            httpexceptions.HTTPServiceUnavailable(),
            errno=ERRORS.BACKEND,
            message="Unable to connect the server.",
        )
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=custom_503
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=503)
        self.assertFormattedError(
            response, 503, ERRORS.BACKEND, "Service Unavailable", "Unable to connect the server."
        )

    def test_integrity_errors_are_served_as_409(self):
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters",
            side_effect=storage_exceptions.IntegrityError,
        ):
            response = self.app.get(self.sample_url, headers=self.headers, status=409)
        self.assertFormattedError(
            response,
            409,
            ERRORS.CONSTRAINT_VIOLATED,
            "Conflict",
            "Integrity constraint violated, please retry.",
        )
        self.assertIn("Retry-After", response.headers)

    def test_500_provides_traceback_on_server(self):
        mock_traceback = mock.patch("logging.traceback.print_exception")
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=ValueError
        ):
            with mock_traceback as mocked_traceback:
                self.app.get(self.sample_url, headers=self.headers, status=500)
                self.assertTrue(mocked_traceback.called)
                self.assertEqual(ValueError, mocked_traceback.call_args[0][0])

    def test_500_logs_request_information(self):
        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=ValueError
        ):
            with mock.patch("kinto.core.views.errors.logger") as mocked_logger:
                self.app.get(self.sample_url + "?q=-42", headers=self.headers, status=500)

        self.assertTrue(mocked_logger.error.called)
        self.assertEqual(
            mocked_logger.error.call_args[1]["extra"],
            {"errno": 999, "method": "GET", "path": "/v0/mushrooms", "querystring": {"q": "-42"}},
        )

    def test_500_logs_errno_from_exception(self):
        custom_error = ValueError("Some error")
        custom_error.errno = ERRORS.VERSION_NOT_AVAILABLE

        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=custom_error
        ):
            with mock.patch("kinto.core.views.errors.logger") as mocked_logger:
                self.app.get(self.sample_url, headers=self.headers, status=500)
        self.assertTrue(mocked_logger.error.called)
        self.assertEqual(mocked_logger.error.call_args[1]["extra"]["errno"], 116)

    def test_500_passes_exception_as_exc_info(self):
        custom_error = ValueError("Some error")

        with mock.patch(
            "tests.core.testapp.views.Mushroom._extract_filters", side_effect=custom_error
        ):
            with mock.patch("kinto.core.views.errors.logger") as mocked_logger:
                self.app.get(self.sample_url, headers=self.headers, status=500)
        self.assertTrue(mocked_logger.error.called)
        self.assertEqual(mocked_logger.error.call_args[1]["exc_info"], custom_error)


class RedirectViewTest(FormattedErrorMixin, BaseWebTest, unittest.TestCase):
    api_prefix = ""

    def test_do_not_redirect_to_version_if_not_supported_version(self):
        resp = self.app.get("/v1/", status=404)
        self.assertFormattedError(
            resp,
            404,
            ERRORS.VERSION_NOT_AVAILABLE,
            "Not Found",
            "The requested API version is not available on this server.",
        )

    def test_redirect_to_version(self):
        # GET on the hello view.
        response = self.app.get("/")
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location, "http://localhost/v0/")

        # GET on the fields view.
        response = self.app.get("/mushrooms")
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location, "http://localhost/v0/mushrooms")

    def test_redirects_benefits_from_cors_setup(self):
        headers = {"Origin": "lolnet.org", "Access-Control-Request-Method": "GET"}
        resp = self.app.options("/", headers=headers, status=200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)

    def test_do_not_redirect_to_version_if_disabled_in_settings(self):
        # GET on the hello view.
        app = self.make_app({"version_prefix_redirect_enabled": False})
        app.get("/", status=404)

    def test_querystring_is_preserved_during_redirection(self):
        response = self.app.get("/home/articles?_since=42")
        self.assertEqual(response.location, "http://localhost/v0/home/articles?_since=42")

    def test_redirection_does_not_allow_crlf(self):
        self.app.get("/crlftest%0DSet-Cookie:test%3Dtest%3Bdomain%3D.yelp.com", status=404)

    def test_redirection_does_not_allow_control_characters(self):
        self.app.get("/9l2j7%0A21m2n", status=404)

    def test_redirection_allows_unicode_characters(self):
        # URL with unicode: /crlftest嘊/
        self.app.get("/crlftest%E5%98%8A/", status=307)

    def test_redirection_allows_unicode_characters_in_querystring(self):
        # URL with unicode: /crlftest?name=嘊
        self.app.get("/crlftest?name=%E5%98%8A", status=307)


class TrailingSlashRedirectViewTest(FormattedErrorMixin, BaseWebTest, unittest.TestCase):
    def test_doesnt_redirect_the_home_page(self):
        response = self.app.get("/")
        self.assertEqual(response.status_int, 200)

    def test_does_redirect_the_version_prefix(self):
        response = self.app.get("")
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location, "http://localhost/v0/")

    def test_it_redirects_if_it_ends_with_a__slash_(self):
        response = self.app.get("/mushrooms/")
        self.assertEqual(response.status_int, 307)
        self.assertEqual(response.location, "http://localhost/v0/mushrooms")

    def test_do_not_redirect_if_disabled_in_settings(self):
        app = self.make_app({"trailing_slash_redirect_enabled": False})
        app.get("/", status=200)
        app.get("/mushrooms/", status=404)

    def test_querystring_is_preserved_during_redirection(self):
        response = self.app.get("/home/articles/?_since=42")
        self.assertEqual(response.location, "http://localhost/v0/home/articles?_since=42")

    def test_it_does_not_redirect_if_the_url_exists(self):
        self.app.get("/static/", status=200)

    def test_display_an_error_message_if_disabled_in_settings(self):
        app = self.make_app({"trailing_slash_redirect_enabled": False})
        response = app.get("", status=404)
        self.assertFormattedError(
            response,
            404,
            ERRORS.MISSING_RESOURCE,
            "Not Found",
            "The resource you are looking for could not be found.",
        )
